# -*- coding: utf-8 -*-`
"""api.py - Create and configure the Game API exposing the resources.
This can also contain game logic. For more complex games it would be wise to
move game logic to another file. Ideally the API will be simple, concerned
primarily with communication to/from the API's users."""


import logging
import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from models import User, Game, Move, Position, Ship, SHIPS, BOARD_SIZE
from models import StringMessage, NewGameForm, GameForm, PositionForm
from models import MakeMoveForm, MoveResponse, MultiGamesMessage, GameRankings, RankLineItem
from models import FullGameInfo, MoveMessage, ShipMessage, XYMessage
from utils import get_by_urlsafe


GET_GAME_REQUEST = endpoints.ResourceContainer(
        urlsafe_game_key=messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))

NEW_POSITION_FORM = endpoints.ResourceContainer(
                        PositionForm,
                        urlsafe_game_key=messages.StringField(1, required=True))

GET_USER_GAMES = endpoints.ResourceContainer(user_name=messages.StringField(1))

@endpoints.api(name='battleship', version='v1')
class BattleshipApi(remote.Service):
    """Game API"""
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username"""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                    'A User with that name already exists!')
        user = User(name=request.user_name, email=request.email)
        user.put()
        return StringMessage(message='User {} created!'.format(
                request.user_name))

    @endpoints.method(request_message=NewGameForm,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game"""
        p1 = User.by_name(request.player_1)
        if request.player_2:
            p2 = User.by_name(request.player_2)
        else:
            p2 = none
        if not p1 or not p2:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        try:
            game = Game.new_game(p1.key, p2.key)
        except:
            raise endpoints.BadRequestException('bad request!')

        # Use a task queue to update the average attempts remaining.
        # This operation is not needed to complete the creation of a new game
        # so it is performed out of sequence.
        # taskqueue.add(url='/tasks/cache_average_attempts')
        return game.to_form('Good luck playing Battleship!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            return game.to_form('Time to make a move!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=NEW_POSITION_FORM,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}/position',
                      name='place_ship',
                      http_method='POST')
    def place_ship(self, request):
        """Places a ship at an x,y coord. Returns a game state with message"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if not game:
            raise endpoints.NotFoundException('Game not found!')

        if game.status == 'game over':
            raise endpoints.BadRequestException('Game already over!')

        if game.status == 'p1 move' or game.status == 'p2 move':
            raise endpoints.BadRequestException('Game already in progress! ' + game.status)

        player = User.by_name(request.user_name)
        if not player:
            raise endpoints.NotFoundException('User does not exist!')
        if player.key != game.p1 and player.key != game.p2:
            raise endpoints.BadRequestException('User is not playing that game.')

        remaining_tup = game.remaining_ships_to_setup()
        if player.key == game.p1:
            player_num = 1
        if player.key == game.p2:
            player_num = 2

        # if submitted ship still needs to be placed, try adding the ship
        if request.ship in remaining_tup[player_num - 1]:
            try:
                game.add_ship(player_num, request.ship, request.x, request.y, request.vertical_orientation)
            except:
                raise endpoints.BadRequestException('Invalid position or ship! ' + ('The remaining ships for that player are ' + ', '.join(remaining_tup[player_num - 1]) or 'No ships remaining to place.'))

            remaining = game.remaining_ships_to_setup()
            ship_list = remaining[player_num - 1]
            if ship_list:
                msg = 'Success! ' + request.user_name + ' needs to add ' + ', '.join(ship_list) + '.'
            else:
                msg = 'Success! No remaining ships to add, ' + request.user_name + '.'

            # if there are not ships remaining to be added to the board, let the game begin
            if not remaining[0] and not remaining[1]:
                game.status = 'p1 move'
                game.put()
            return game.to_form(msg)

        # exception for submitting a ship that is already on the board or invalid ship
        raise endpoints.BadRequestException('Not a valid move. ' + ('The remaining ships for that player are ' + ', '.join(remaining_tup[player_num - 1]) or 'No ships remaining to place.'))


    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=MoveResponse, #hit, ship, sunk
                      path='game/{urlsafe_game_key}/move',
                      name='make_move',
                      http_method='POST')
    def make_move(self, request):
        """Makes a move. Returns a game state with message"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        player = User.by_name(request.user_name)

        # preflight checks for valid request
        if not player:
            raise endpoints.BadRequestException('User not found!')
        if game.status == 'game over':
            raise endpoints.BadRequestException('Game already over!')
        if game.status == 'setting up':
            raise endpoints.BadRequestException('Game not ready yet! Place your ships.')
        if game.p1 != player.key and game.p2 != player.key:
            raise endpoints.BadRequestException('The specified user is not playing the specified game.')

        #  determine who is making a move and if it's really their turn
        if game.p1 == player.key:
            opponent = game.p2.get()
            if game.status == 'p2 move':
                raise endpoints.BadRequestException('Error: It is ' + opponent.name + '\'s turn!')
        else:
            opponent = game.p1.get()
            if game.status == 'p1 move':
                raise endpoints.BadRequestException('Error: It is ' + opponent.name + '\'s turn!')

        ## coordinates
        x = int(request.x)
        y = int(request.y)

        if x not in range(BOARD_SIZE) or y not in range(BOARD_SIZE):
            raise endpoints.BadRequestException('Attempted move is off the board.')

        # attempt move
        if Move.get_move(game, player, x, y):
            raise endpoints.BadRequestException('You already made that move')

        # we have determined player is making a valid move, so switch whose turn it is
        if game.status == 'p1 move':
            game.status = 'p2 move'
        else:
            game.status = 'p1 move'
        game.put()

        # create a Move object
        move = Move(parent=game.key, player=player.key, x=x, y=y)
        move.put()


        # check for hits
        ships = Ship.query(ancestor=game.key).filter(Ship.player==opponent.key).fetch()
        position = None # position that was hit, if any
        ship = None # ship that was hit, if any
        to_put = []
        for s in ships:
            position = Position.query(ancestor=s.key).filter(Position.x==x,Position.y==y).get()

            if position:
                position.hit = True
                position.put()
                positions = Position.query(ancestor=s.key).fetch()
                hit_positions = [p for p in positions if p.hit == True]

                if positions == hit_positions:
                    s.sunk = True
                    s.put()
                    sunk_ships = [sunk for sunk in ships if sunk.sunk == True]

                    if sunk_ships == ships:
                        game.status = 'game over'
                        game.winner = player.key
                        game.put()

                        # send game-over email
                        message = '{} sunk {}! The game is over and {} won!'.format(player.name, s.ship, player.name)
                        self.sendEmail(player, game, message)
                        self.sendEmail(opponent, game, message)

                        # return game over MoveResponse
                        return MoveResponse(hit=True, ship=s.ship, sunk=True, message='Hit! Sunk! Game over! You win!')


                    #return sunk ship message
                    message = 'Your turn! {} sunk your {}!'.format(player.name, s.ship)
                    self.sendEmail(opponent, game, message)

                    return MoveResponse(hit=True, ship=s.ship, sunk=True, message="Hit! Sunk "+ s.ship + "!")

                # hit message sent to opponent
                message = 'Your turn! {} hit your {}!'.format(player.name, s.ship)
                self.sendEmail(opponent, game, message)
                # return hit message
                return MoveResponse(hit=True, ship=s.ship, sunk=False, message="Hit on "+ s.ship + "!")

        message = 'Your turn! {} missed at {}, {}!'.format(player.name, x, y)
        self.sendEmail(opponent, game, message)
        # no match for a ship at x, y, so return a Miss message
        return MoveResponse(hit=False, message='Miss at '+ str(x) + ' , ' + str(y) +'!')


    @endpoints.method(request_message=GET_USER_GAMES,
                      response_message=MultiGamesMessage,
                      path='get_user_games/{user_name}',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        ''' returns all games the specified user has in progress '''
        user = User.by_name(request.user_name)
        if not user:
            raise endpoints.NotFoundException('User not found')

        games = Game.query().filter(
                    ndb.OR(Game.p1==user.key, Game.p2==user.key)).filter(
                    Game.status != 'game over').fetch()

        games.sort(key= lambda a: a.created)

        response = MultiGamesMessage(
                        games=[game.to_form('') for game in games],
                        user=request.user_name)
        return response


    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=StringMessage,
                      path='game/{urlsafe_game_key}',
                      name='cancel_game',
                      http_method='DELETE')
    def cancel_game(self, request):
        ''' cancel a game. This just deletes the game from the db. '''

        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if not game:
            raise endpoints.NotFoundException('Game not found')

        if game.status == 'game over':
            raise endpoints.BadRequestException(
                'You can\'t delete a game that is already over')

        try:
            game.delete_game()
            return StringMessage(message='Game with id ' + request.urlsafe_game_key + 'successfully deleted.')
        except:
            raise endpoints.BadRequestException(
                'An error was found in the request.')


    @endpoints.method(response_message=GameRankings,
                      path='get_user_rankings',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        ''' returns user rankings, ordered by wins '''
        games = Game.query(Game.status == 'game over').fetch()
        users = User.query().fetch()
        rankings = {u.key: {"name": u.name, "wins": 0} for u in users}
        for g in games:
            if g.winner in rankings.keys():
                rankings[g.winner]["wins"] += 1
        rankings = [RankLineItem(user_name=rankings[r]["name"], wins=rankings[r]["wins"]) for r in rankings]
        rankings.sort(key= lambda u: int(u.get_assigned_value("wins"))*(-1))
        return GameRankings(rankings=rankings)




    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=FullGameInfo,
                      path='game_history/{urlsafe_game_key}',
                      name='game_history',
                      http_method='GET')
    def get_game_history(self, request):
        ''' returns the usual GameForm, plus all related positions and all moves '''
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if not game:
            return endpoints.NotFoundException("Game not found")
        game_key = game.key
        game = game.to_form("")

        ships = Ship.query(ancestor=game_key).order(-Ship.created).fetch()
        ship_forms = []
        for s in ships:
            position_forms = []
            positions = Position.query(ancestor=s.key).fetch()
            for p in positions:
                position_forms.append(XYMessage(x=p.x, y=p.y, hit=p.hit))
            ship_forms.append(ShipMessage(
                                player=s.player.get().name,
                                ship=s.ship,
                                created_date=s.created,
                                positions=position_forms))

        moves = Move.query(ancestor=game_key).order(-Move.created).fetch()
        move_forms = []
        for m in moves:
            move_forms.append(MoveMessage(player=m.player.get().name, x=m.x, y=m.y, created_date=m.created))

        form = FullGameInfo(game=game, ships=ship_forms, moves=move_forms)
        return form



    def sendEmail(self, user, game, message):
        if user.email: # don't try to send emails to users who don't have that property
            task = taskqueue.add(
                    method='POST',
                    url='/sendemail',
                    params={'user_name': user.name, 'game_id': game.key.urlsafe(), 'user_email': user.email, 'message': message})


api = endpoints.api_server([BattleshipApi])
