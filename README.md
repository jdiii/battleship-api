# Battleship
Battleship API created as part of the Game API project in the Udacity full-stack nanodegree.

## Set-Up Instructions:
0. Install the [Google Cloud SDK](https://cloud.google.com/sdk/)
1. Clone this repo to your computer with `git clone https://github.com/jdiii/battleship-api.git`
2. `cd` to the newly created directory and run the app with the devserver using the command `dev_appserver.py app.yaml`. Ensure it's
 running by visiting the API Explorer, which by default runs at https://localhost:8080/_ah/api/explorer.

## Game Description:
Battleship is a two-player game where each player tries to shoot and sink all her opponent's ships.

## How to play, in brief:
1. Set up two users using the `/user` endpoint
2. In the setup phase of the game, each player sends requests to the `/game/{urlsafe_game_key}/position` endpoint to place all 5 ships in his fleet (Destroyer, Cruiser, Submarine, Battleship, and Aircraft Carrier) on his 10x10 board.
3. Once all the ships are placed on the board, the game starts. Players take turns shooting at the other player's ships using the `/game/{urlsafe_game_key}/move` endpoint.
4. The first player who sinks all of her opponent's ships wins.

## How To Play
This is the game sequence with example posts provided.

### Set up users
Battleship is a two player game, so creating two players is required before playing.
    * POST to the `create_user` method with `user_name="player1"`
    * POST to the `create_user` method with `user_name="player2"`

### Set up a new game.
POST to `new_game` endpoint with params `player_1='player_1', player_2='player2'`.

Important: Note the `urlsafe_game_key` returned by this method, as you'll need it for the rest of the game! I will refer to it as {{game_key}} for the rest of this example.

### Set up the board
Each player needs to place all five ships on their 10x10 "board" using the `place_ship` endpoint. The five ships are Aircraft Carrier (length=5), Battleship (4), Cruiser (3), Destroyer (2), and Submarine (3). Here is an example sequence:
    * POST to `place_ship` with params:
        * `urlsafe_game_key={{game key}}`
        * `user_name='player1'`
        * `ship='Aircraft Carrier'`
        * `vertical_orientation=True`
        * `x=1`
        * `y=1`
    * POST to `place_ship` with params:
        * `urlsafe_game_key={{game key}}`
        * `user_name='player1'`
        * `ship='Battleship'`
        * `vertical_orientation=True`
        * `x=2`
        * `y=1`
    * POST to `place_ship` with params:
        * `urlsafe_game_key={{game key}}`
        * `user_name='player1'`
        * `ship='Cruiser'`
        * `vertical_orientation=True`
        * `x=5`
        * `y=2`
    * POST to `place_ship` with params:
        * `urlsafe_game_key={{game key}}`
        * `user_name='player1'`
        * `ship='Submarine'`
        * `vertical_orientation=True`
        * `x=9`
        * `y=3`
    * POST to `place_ship` with params:
        * `urlsafe_game_key={{game key}}`
        * `user_name='player1'`
        * `ship='Destroyer'`
        * `vertical_orientation=False`
        * `x=2`
        * `y=8`
Repeat those steps with user_name=`player2` and the game will be ready!

Note the (x,y) coordinate provided with be the top-left-most point of the ship and `vertical_orientation` determines whether the ship's length will span the x-axis or y-axis of the board. For example, placing the Destroyer at (2,8) with `vertical_orientation=False` means it will be located at (2,8), (3,8), (4,8).

### Play the game
The game consists of players taking turns shooting at each other's ships. Whichever player hits all of the other player's positions first wins. Use the `make_move` endpoint to take shots:
    * Player 1 fires by POSTing to `make_move` with params:
        * `urlsafe_game_key={{game_key}}`
        * `user_name=player1`
        * `x=1`
        * `x=2`
      Since player2 placed an Aircraft Carrier there, this request will return a hit message.
    * Player 2 fires by POSTing to `make_move` with params:
        * `urlsafe_game_key={{game_key}}`
        * `user_name=player2`
        * `x=5`
        * `y=5`
      Player1 didn't place a ship there, so the request will return a miss message.

Players alternate hitting the `make_move` endpoint until one player destroys all the other's ships.

## Files Included:
 - api.py: Contains endpoints and game playing logic.
 - app.yaml: App configuration.
 - cron.yaml: Cronjob configuration.
 - main.py: Handler for taskqueue handler.
 - models.py: Entity and message definitions including helper methods.
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string.

## Cron jobs
Email notifications are sent to all players whose turn it is in a game every 24 hours.

## Notifications
Email notifications are sent after each move to notify the player of their turn (or if the game ends).

## Endpoints Included:
 - **create_user**
    - Path: 'user'
    - Method: POST
    - Parameters: user_name, email (optional)
    - Returns: Message confirming creation of the User.
    - Description: Creates a new User. user_name provided must be unique. Will
    raise a ConflictException if a User with that user_name already exists.

 - **new_game**
    - Path: 'game'
    - Method: POST
    - Parameters: user_name, min, max, attempts
    - Returns: GameForm with initial game state.
    - Description: Creates a new Game. user_name provided must correspond to an
    existing user–otherwise a NotFoundException is raised.

 - **get_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Returns the current state of a game. Raises NotFoundException if game key is not valid.

 - **place_ship**
    - Path: 'game/{urlsafe_game_key}/position'
    - Method: POST
    - Parameters: urlsafe_game_key, x, y, user_name, ship, vertical_orientation
    - Returns: GameForm with success message.
    - Description: Accepts a (x,y) position and orientation boolean for a ship in the setup phase of the game (the ships may be oriented horizontally or vertically on the board starting at the given x,y coordinate). Raises exceptions if position is invalid, the requested ship is already in place, or if the game already started.

 - **make_move**
    - Path: 'game/{urlsafe_game_key}/move'
    - Method: POST
    - Parameters: urlsafe_game_key, x, y, user_name
    - Returns: MoveResponse with hit/miss information.
    - Description: Accepts a (x,y) position for a move. Returns a message as to whether the move was a hit on an opponent's ship. Raises exceptions if move or user was invalid, or if it's not the user's turn. If the move sinks the final ship of the opponent, the game status becomes 'game over' and the player who made the move wins.

 - **get_user_games**
    - Path: 'get_user_games/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: MultiGamesMessage
    - Description: Returns all games played by the provided player. Will raise a NotFoundException if the User does not exist.

 - **cancel_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: DELETE
    - Parameters: urlsafe_game_key
    - Returns: StringMessage
    - Description: Deletes game. Raises NotFoundException if game key provided isn't found.

 - **get_user_rankings**
    - Path: 'game_user_rankings'
    - Method: GET
    - Parameters: None
    - Returns: GameRankings
    - Description: Returns list of all users ordered by # of wins.

 - **get_game_history**
    - Path: 'game_history/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: FullGameInfo
    - Description: Returns detailed game history for requested game including all moves, all ships, and all ship positions.
