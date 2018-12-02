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

import os
import datetime

#
#
#
DIRECTIONS = {
    "n": Direction.North,
    "s": Direction.South,
    "e": Direction.East,
    "w": Direction.West
}

#
#
#
def spawnShip(game):
    nShips = len(game.me.get_ships())

    if game.turn_number <= 200:
        maxShips = 8
    elif game.turn_number <= 350:
        maxShips = 6
    else:
        maxShips = 5

    if nShips >= maxShips:
        return False

    if game.me.halite_amount < constants.SHIP_COST:
        return False

    if game.game_map[me.shipyard].is_occupied:
        return False

    entryExitCells = game.me.shipyard.position.get_surrounding_cardinals()

    for pos in entryExitCells:
        if game.game_map[pos].is_occupied:
            ship = game.game_map[pos].ship
            #logging.info("Game - Shipyard cell {} is occuplied by a {} ship {} owned by {} ".format(pos, ship.status, ship.id, ship.owner))
            return False

    return True

#
# destination - The direction the ship is trying to go.  Backoff will be opposite
#
def getBackoffPoint(game, ship, destination):
    destinationMoves = game.game_map.get_unsafe_moves(ship.position, destination)

    if len(destinationMoves) == 0:
        return ship.position

    choice = random.choice(destinationMoves)
    backoffDirection = Direction.invert(choice)

    mult = random.randint(1, 8)

    backoffPoint = ship.position + Position(backoffDirection[0] * mult, backoffDirection[1] * mult)
    logging.info("Ship - Ship {} backoffPoint {}".format(ship.id, backoffPoint))

    return backoffPoint

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

# create a bot name based on version.txt
if os.path.exists("./version.txt"):
    try:
        version_file = open("./version.txt", 'r')
        version = version_file.read().strip()
        version_file.close()
    except IOError:
        logging.info("Version file read failed")
        version = "X"
else:
    version = "X"

BotName = "MyBot.v6"

#
# game start
#

game.ready(BotName)

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
# Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}. {}".format(game.my_id, "{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now())))

""" <<<Game Loop>>> """

while True:
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
                "status": "exloring",
                "path": []
            }
            ship.status = ship_states[ship.id]["status"]
            ship.path = ship_states[ship.id]["path"]

        logging.info("Game - Ship {} at {} has {} halite and is {}".format(ship.id, ship.position, ship.halite_amount, ship.status))

        # state - returning
        if ship.status == "returning":
            if ship.position == me.shipyard.position:
                logging.info("Ship - Ship {} completed a Drop-off".format(ship.id))
                ship.status = "exploring"
            else:
                dropoffs = me.get_dropoffs()
                destinations = list(dropoffs) + [me.shipyard.position]

                minDistance = False
                movePosition = False
                move = False

                for dest in destinations:
                    distance = game_map.calculate_distance(ship.position, dest)
                    if minDistance == False or distance < minDistance:
                        minDistance = distance
                        movePosition = dest

                move =  Direction.convert(game_map.naive_navigate(ship, movePosition))

                logging.info("Ship - Ship {} initial move1: {}".format(ship.id, move))

                if move == "o":
                    logging.info("Ship - Ship {} Collision returning".format(ship.id))
                    ship.status = "backingoff"
                    ship.path.append(getBackoffPoint(game, ship, dest))
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
            logging.info("Ship - ship {} is backing off".format(ship.id))
            backoff_position = ship.path[0]
            if ship.position == backoff_position:
                logging.info("Ship - ship {} backing off is complete at {}".format(ship.id, backoff_position))
                ship.status = "returning"
                ship.path.pop()

        # state - exloring
        elif ship.halite_amount >= constants.MAX_HALITE / 4:
            logging.info("Ship - ship {} is now returning".format(ship.id))
            ship.status = "returning"

        # Move
        if game_map[ship.position].halite_amount < constants.MAX_HALITE / 10 or ship.is_full:
            if len(ship.path):
                move = Direction.convert(game_map.naive_navigate(ship, ship.path[0]))
                logging.info("Ship - ship {} backoffMove: {}".format(ship.id, move))
            else:
                moveChoice = random.choice(["n", "s", "e", "w"])
                #logging.info("Ship - ship {} moveChoice2: {}".format(ship.id, moveChoice))

                moveOffset = ship.position.directional_offset(DIRECTIONS[moveChoice])
                #logging.info("Ship - ship {} moveOffset2: {}".format(ship.id, moveOffset))

                move = Direction.convert(game_map.naive_navigate(ship, moveOffset))
                #logging.info("Ship - ship {} final move2: {}".format(ship.id, move))

                if moveChoice != move:
                    logging.info("Ship - ship {} Collision, original {}, corrected {}".format(ship.id, moveChoice, move))

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
    if spawnShip(game):
        command_queue.append(me.shipyard.spawn())
        logging.info("Game - Ship spawn")

    #logging.info("Game - commad queue: {}".format(command_queue))

    #logging.info("Game - end ship_states: {}".format(ship_states))

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)
