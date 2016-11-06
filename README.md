# Battleship
Battleship API created as part of the Game API project in the Udacity full-stack nanodegree.

## Set-Up Instructions:
0. Install the [Google Cloud SDK](https://cloud.google.com/sdk/)
1. Clone this repo to your computer with `git clone https://github.com/jdiii/battleship-api.git`
2. `cd` to the newly created directory and run the app with the devserver using the command `dev_appserver.py app.yaml`. Ensure it's
 running by visiting the API Explorer, which by default runs at https://localhost:8080/_ah/api/explorer.

## Game Description:
Battleship is a two-player game where each player tries to shoot and sink all her opponent's ships.

## How to play:
1. Set up two users using the `/user` endpoint
2. In the setup phase of the game, each player sends requests to the `/game/{urlsafe_game_key}/position` endpoint to place all 5 ships in his fleet (Destroyer, Cruiser, Submarine, Battleship, and Aircraft Carrier) on his 10x10 board.
3. Once all the ships are placed on the board, the game starts. Players take turns shooting at the other player's ships using the `/game/{urlsafe_game_key}/move` endpoint.
4. The first player who sinks all of her opponent's ships wins.

## Files Included:
 - api.py: Contains endpoints and game playing logic.
 - app.yaml: App configuration.
 - cron.yaml: Cronjob configuration.
 - main.py: Handler for taskqueue handler.
 - models.py: Entity and message definitions including helper methods.
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string.

## Cron jobs
Email notifications are sent to all players whose turn it is in a game every hour.

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
    - Parameters: urlsafe_game_key, x, y, user_name, ship
    - Returns: GameForm with success message.
    - Description: Accepts a (x,y) position for a ship in the setup phase of the game. Raises exceptions if position is invalid, the requested ship is already in place, or if the game already started.

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

##Models Included:
 - **User**
    - Stores unique user_name and (optional) email address.

 - **Game**
    - Stores unique game states. Associated with User model via KeyProperty.

 - **Move**
 	- Stores player moves in terms of x and y on the opponent's board. Child of Game.

 - **Ship**
    - Stores ship information, including name, owner, status. Child of Game. A ship will have several child Positions representing where the ship is located and where it's been hit by opponent Moves.

 - **Position**
    - Stores x, y coordinate of ships and whether position has been hit. Child of Ship.

## Messages Included:
 - **GameForm**
    - Representation of a Game's state.
 - **PositionForm**
    - Position form for inbound requests to place a ship on the game board.
 - **NewGameForm**
    - Used to create a new game between player_1 and player_2
 - **MakeMoveForm**
    - Inbound form for a user to take a shot at an x, y coordinate on the opponent's board.
 - **MoveResponse**
    - Outbound form to respond to a MakeMoveForm, including whether a ship was missed, hit, or sunk.
 - **MultiGamesMessage**
    - Used to list all of a user's games.
 - **RankLineItem**
    - Used to represent a user's win total in a GameRankings message.
 - **GameRankings**
    - Used to list user rankings.
 - **XYMessage**
    - Simple representation of a ship's coordinate on the board and whether it's been hit. Used for FullGameInfo.
 - **ShipMessage**
    - Representation of a Ship and its associated Positions. Used for FullGameInfo.
 - **MoveMessage**
    - Simple representation of a Move. Used for FullGameInfo.
 - **FullGameInfo**
    - Detailed representation of a game's full history, with all child Ships and Moves.
 - **StringMessage**
    - General purpose String container.

## Technologies Used
Built on Google App Engine, Cloud Data Store, Google Protocol RPC in Python
