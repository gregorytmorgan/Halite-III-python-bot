#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction
from hlt.positionals import Position

# This library allows you to generate random numbers.
import random

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging
import datetime
import time

#
#
#
DIRECTIONS = {
    "n": Direction.North,
    "s": Direction.South,
    "e": Direction.East,
    "w": Direction.West
}

def get_random_move(ship):

    moveChoice = random.choice(["n", "s", "e", "w"])
    #logging.info("Ship - get_random_move() - ship {} moveChoice2: {}".format(ship.id, moveChoice))

    moveOffset = ship.position.directional_offset(DIRECTIONS[moveChoice])
    #logging.info("Ship - get_random_move() - ship {} moveOffset2: {}".format(ship.id, moveOffset))

    move = Direction.convert(game_map.naive_navigate(ship, moveOffset))
    #logging.info("Ship - get_random_move() - ship {} final move2: {}".format(ship.id, move))

    if move == "o":
        for i in range(4):
            # get char direction vs alt code below so we can log consistent msg
            # alt code: ship.move(random.choice([Direction.North, Direction.South, Direction.East, Direction.West]))
            moveChoice = random.choice(["n", "s", "e", "w"])
            moveOffset = ship.position.directional_offset(DIRECTIONS[moveChoice])
            move = Direction.convert(game_map.naive_navigate(ship, moveOffset))
            if move != "o":
                break

        if move == "o":
            logging.info("Ship - get_random_move() - ship {} Collision, original {}, correct failed".format(ship.id, moveChoice))
        else:
            logging.info("Ship - get_random_move() -  ship {} Collision, original {}, corrected {}".format(ship.id, moveChoice, move))

    return move

#
#
#
def spawn_ship(game):
    nShips = len(game.me.get_ships())

    if game.turn_number <= 100:
        maxShips = 8
    elif game.turn_number <= 200:
        maxShips = 6
    elif game.turn_number <= 300:
        maxShips = 4
    else:
        maxShips = 2

    if nShips >= maxShips:
        return False

    if game.me.halite_amount < constants.SHIP_COST:
        return False

    if game.game_map[me.shipyard].is_occupied:
        return False

    entryExitCells = game.me.shipyard.position.get_surrounding_cardinals()

    for pos in entryExitCells:
        if game.game_map[pos].is_occupied:
            return False

    return True

#
# destination - The direction the ship is trying to go.  Backoff will be opposite
#
def get_backoff_point(game, ship, destination):
    destinationMoves = game.game_map.get_unsafe_moves(ship.position, destination)

    if len(destinationMoves) == 0:
        return ship.position

    choice = random.choice(destinationMoves)
    backoffDirection = Direction.invert(choice)

	# when there's a collion, we backoff between 1 and nShips/2 cells
    mult = random.randint(1, round(len(game.me.get_ships()) / 2))

    backoffPoint = ship.position + Position(backoffDirection[0] * mult, backoffDirection[1] * mult)

    # if the backup point wrap, truncate it to the edge to prevent simple nav from failing
    if backoffPoint.x > game.game_map.width - 1:
        backoffPoint.x = game.game_map.width - 1

    if backoffPoint.x < 0:
        backoffPoint.x = 0

    if backoffPoint.y > game.game_map.height - 1:
        backoffPoint.y = game.game_map.height - 1

    if backoffPoint.y <    0:
        backoffPoint.y = 0

    logging.info("Ship - get_backoff_point() - ship {} backoffPoint {}".format(ship.id, backoffPoint))

    return backoffPoint

#
#
#
def get_dropoff_position(ship):
    dropoffs = me.get_dropoffs()
    destinations = list(dropoffs) + [me.shipyard.position]

    minDistance = False
    movePosition = False

    for dest in destinations:
        distance = game_map.calculate_distance(ship.position, dest)
        if minDistance == False or distance < minDistance:
            minDistance = distance
            movePosition = dest

    return movePosition

#
# main
#

""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()

# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.

# keep ship state inbetween turns
ship_states = {}

BotName = "MyBot"

#
# game start
#

game.ready(BotName)

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
# Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}. {}".format(game.my_id, "{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now())))

""" <<<Game Loop>>> """

while True:
    TurnStartTime = time.time()

    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    # running update_frame().
    game.update_frame()

    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    # end of the turn.
    command_queue = []

    #logging.info("Game - begin ship_states: {}".format(ship_states))

    for ship in me.get_ships():
        # For each of your ships, move randomly if the ship is on a low halite location or the ship is full.
        # Else, collect halite.

        if ship.id in ship_states:
            ship.status = ship_states[ship.id]["status"]
            ship.path = ship_states[ship.id]["path"]
        else:
            logging.info("Game - New ship with ID {}".format(ship.id))
            ship_states[ship.id] = {
                "status": "exploring",
                "path": []
            }
            ship.status = ship_states[ship.id]["status"]
            ship.path = ship_states[ship.id]["path"]

        logging.info("Game - Ship {} at {} has {} halite and is {}".format(ship.id, ship.position, ship.halite_amount, ship.status))

        # state - returning
        if ship.status == "returning":
            if ship.position == me.shipyard.position:
                logging.info("Ship - Ship {} completed a Dropoff".format(ship.id))
                ship.path.clear()
                ship.status = "exploring"
            else:
                dropoff_position = get_dropoff_position(ship)

                move =  Direction.convert(game_map.naive_navigate(ship, dropoff_position))

                logging.info("Ship - Ship {} initial move1: {}".format(ship.id, move))

                if move == "o":
                    logging.info("Ship - Ship {} Collision returning".format(ship.id))
                    ship.status = "backingoff"
                    ship.path.append(get_backoff_point(game, ship, dropoff_position))
                else:
                    fuelCost = round(game_map[ship.position].halite_amount * .1, 2)
                    if fuelCost > ship.halite_amount:
                        logging.info("Ship - Ship {} has insuffient fuel. Have {}, need {}".format(ship.id, ship.halite_amount, fuelCost))
                        move = "o"

                command_queue.append(ship.move(move))

                # save the ship state
                ship_states[ship.id]["status"] = ship.status
                ship_states[ship.id]["path"] = ship.path

                continue

        # state - backoff
        elif ship.status == "backingoff":
            logging.info("Ship - ship {} is backing off to {}".format(ship.id, ship.path[len(ship.path) - 1]))
            backoff_position = ship.path[len(ship.path) - 1]
            if ship.position == backoff_position:
                logging.info("Ship - ship {} backing off is complete at {}".format(ship.id, backoff_position))
                ship.status = "returning"
                ship.path.pop()
                ship.path.append(get_dropoff_position(ship))

        # state - exploring / state change
        elif ship.halite_amount >= constants.MAX_HALITE / 4:
            logging.info("Ship - ship {} is now returning".format(ship.id))
            ship.status = "returning"

        # Move
        #
        # conditions:
        #  1. ignore cells with less than 10% cell capacity (1000)
        #  2. treat 90% ship capacity (1000) as full
        #if game_map[ship.position].halite_amount < constants.MAX_HALITE / 10 or (ship.halite_amount / constants.MAX_HALITE > .9):
        if game_map[ship.position].halite_amount < constants.MAX_HALITE / 10 or ship.is_full:

            if len(ship.path) and ship.position == ship.path[len(ship.path) - 1]:
                ship.path.pop()

            # if we don't have a nav path, then make a random move, otherwise make a nav move.
            # In the case of a nav move, if collision, then just get a one-time random move
            if len(ship.path) == 0:
                move = get_random_move(ship)
            else:
                move = Direction.convert(game_map.naive_navigate(ship, ship.path[len(ship.path) - 1]))
                if move == "o":
                    move = get_random_move(ship)

                if move == "o":
                    logging.info("Ship - ship {} Nav move collision, original {}, correct failed {}".format(ship.id, ship.path[len(ship.path) - 1]))
                else:
                    logging.info("Ship - ship {} Nav move collision, original {}, corrected {}".format(ship.id, ship.path[len(ship.path) - 1], move))

                logging.info("Ship - ship {} Nav Move: {}".format(ship.id, move))

            if move != "o":
                fuelCost = round(game_map[ship.position].halite_amount * .1, 2)
                if fuelCost > ship.halite_amount:
                    logging.info("Ship - Ship {} has insuffient fuel. Have {}, need {}".format(ship.id, ship.halite_amount, fuelCost))
                    move = "o"

            command_queue.append(ship.move(move))
        else:
            command_queue.append(ship.stay_still())

        # save the ship state
        ship_states[ship.id]["status"] = ship.status
        ship_states[ship.id]["path"] = ship.path

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if spawn_ship(game):
        command_queue.append(me.shipyard.spawn())
        logging.info("Game - Ship spawn")

    #logging.info("Game - commad queue: {}".format(command_queue))

    logging.info("Game - end ship_states: {}".format(ship_states))

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)

    logging.info("elapsed turn time: {:.4f}".format(time.time() - TurnStartTime))
