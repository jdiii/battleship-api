"""models.py - This file contains the class definitions for the Datastore
entities used by the Game. Because these classes are also regular Python
classes they can include methods (such as 'to_form' and 'new_game')."""

import random
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb

class GameException(Exception):
    pass

SHIPS = {'Destroyer': 2, 'Cruiser': 3, 'Submarine': 3, 'Battleship': 4, 'Aircraft Carrier': 5}
BOARD_SIZE = 9

## MODELS ########################
class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty(default=None)

    @classmethod
    def by_name(cls, name):
        return User.query(User.name == name).get()


class Move(ndb.Model):
    player = ndb.KeyProperty(required=True, kind="User")
    x = ndb.IntegerProperty(required=True)
    y = ndb.IntegerProperty(required=True)

    @classmethod
    def get_move(cls, game, player, x, y):
        q = cls.query(
            cls.player==player.key,
            cls.x==x,
            cls.y==y,
            ancestor=game.key)
        move = q.get()
        print move
        return move




class Ship(ndb.Model):
    player = ndb.KeyProperty(required=True, kind="User")
    ship = ndb.StringProperty(required=True)
    sunk = ndb.BooleanProperty(required=True, default=False)

class Position(ndb.Model):
    x = ndb.IntegerProperty(required=True)
    y = ndb.IntegerProperty(required=True)
    hit = ndb.BooleanProperty(required=True, default=False)


class Game(ndb.Model):
    """Game object"""
    # statuses: 'setting up', 'p1 move', 'p2 move', 'game over'
    status = ndb.StringProperty(required=True, default='Setting Up')
    p1 = ndb.KeyProperty(required=True, kind='User')
    p2 = ndb.KeyProperty(required=True, kind='User')
    winner = ndb.KeyProperty(kind='User')

    @classmethod
    def new_game(cls, user1, user2):
        """Creates and returns a new game"""
        game = Game(p1=user1,
                    p2=user2)
        game.put()
        return game

    def delete_game(self):
        self.key.delete()

    def get_ships(self, user_key):
        return Ship.query(ancestor=self.key).filter(Ship.player==user_key).fetch()

    def remaining_ships_to_setup(self):
        ships = SHIPS.keys()
        p1_positions = [s.ship for s in self.get_ships(self.p1)]
        p2_positions = [s.ship for s in self.get_ships(self.p2)]
        return ([ship for ship in ships if ship not in p1_positions],
                [ship for ship in ships if ship not in p2_positions])


    @ndb.transactional(xg=True)
    def add_ship(self, player, ship_name, x, y, vertical=False):

        game = self

        if y > BOARD_SIZE or x > BOARD_SIZE or y < 0 or x < 0:
            raise GameException("Requested position is off the board")

        # figure out which player is placing a ship
        if player == 1:
            p_key = self.p1
        else:
            p_key = self.p2

        # create the ship
        ship = Ship(parent=self.key, player=p_key, ship=ship_name)
        ship.put()

        # get previous ships to check for conflicts.
        old_ships = Ship.query(ancestor=self.key).fetch()
        board = []
        for s in old_ships:
            if s.player == p_key: # must check user this way to use transactions
                positions = Position.query(ancestor=s.key).fetch()
                board.extend(positions)
        print board
        board_coords = [(p.x, p.y) for p in board]

        #create the x,y pairs representing where the ship is on the board
        ship_len = SHIPS[ship_name]
        print ship_len
        x_init = x
        y_init = y
        coordinates = []
        if not vertical:
            while x < x_init+ship_len:
                print x
                if x > BOARD_SIZE:
                    raise GameException('Not a valid position')
                if (x, y) in board_coords:
                    raise GameException('Position already occupied')
                coord = Position(parent=ship.key, x=x, y=y)
                coordinates.append(coord)
                x += 1
        else:
            while y < y_init+ship_len:
                if y > BOARD_SIZE:
                    raise GameException('Not a valid position')
                if (x, y) in board_coords:
                    raise GameException('Position already occupied')
                coord = Position(parent=ship.key, x=x, y=y)
                coordinates.append(coord)
                y += 1

        ndb.put_multi(coordinates)



    def to_form(self, message):
        """Returns a GameForm representation of the Game"""
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.p1 = self.p1.get().name
        form.p2 = self.p2.get().name
        form.status = self.status
        form.message = message
        return form

    def end_game(self, won=False):
        """Ends the game - if won is True, the player won. - if won is False,
        the player lost."""
        self.status = 'game over'
        self.put()
        # Add the game to the score 'board'
        score = Score(user=self.user, date=date.today(), won=won,
                      guesses=self.attempts_allowed - self.attempts_remaining)
        score.put()


class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    status = messages.StringField(2, required=True)
    message = messages.StringField(3, required=True)
    p1 = messages.StringField(4, required=True)
    p2 = messages.StringField(5, required=True)


class PositionForm(messages.Message):
    ''' inbound form for creating a ship position '''
    urlsafe_game_key = messages.StringField(1, required=True)
    user_name = messages.StringField(2, required=True)
    ship = messages.StringField(3, required=True)
    x = messages.IntegerField(4, required=True)
    y = messages.IntegerField(5, required=True)
    vertical_orientation = messages.BooleanField(6, required=True, default=False)


class NewGameForm(messages.Message):
    """Used to create a new game"""
    player_1 = messages.StringField(1, required=True)
    player_2 = messages.StringField(2)


class MakeMoveForm(messages.Message):
    """Used to make a move in an existing game"""
    x = messages.IntegerField(1, required=True)
    y = messages.IntegerField(2, required=True)
    user_name = messages.StringField(3, required=True)


class MoveResponse(messages.Message):
    hit = messages.BooleanField(1, required=True)
    ship = messages.StringField(2)
    sunk = messages.BooleanField(3)
    message = messages.StringField(4)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)


class MultiGamesMessage(messages.Message):
    user = messages.StringField(1)
    games = messages.MessageField(GameForm, 2, repeated=True)

class RankLineItem(messages.Message):
    user_name = messages.StringField(1, required=True)
    wins = messages.IntegerField(2, required=True)

class GameRankings(messages.Message):
    rankings = messages.MessageField(RankLineItem, 1, repeated=True)

class XYMessage(messages.Message):
    x = messages.IntegerField(1)
    y = messages.IntegerField(2)
    hit = messages.BooleanField(3)

class ShipMessage(messages.Message):
    player = messages.StringField(1)
    ship = messages.StringField(2)
    positions = messages.MessageField(XYMessage, 3, repeated=True)

class MoveMessage(messages.Message):
    player = messages.StringField(1)
    x = messages.IntegerField(2)
    y = messages.IntegerField(3)

class FullGameInfo(messages.Message):
    game = messages.MessageField(GameForm, 1)
    ships = messages.MessageField(ShipMessage, 2, repeated=True)
    moves = messages.MessageField(MoveMessage, 3, repeated=True)
