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

DIRECTIONS = {
    "n": Direction.North,
    "s": Direction.South,
    "e": Direction.East,
    "w": Direction.West
}

""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()

ship_status = {}

# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.

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

BotName = "MyBot" + version

game.ready(BotName)

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """

while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    command_queue = []

    nShips = len(me.get_ships())

    for ship in me.get_ships():
        # For each of your ships, move randomly if the ship is on a low halite location or the ship is full.
        # Else, collect halite.

        if ship.id not in ship_status:
            ship_status[ship.id] = "exploring"

        logging.info("Ship {} at {} has {} halite and is {}".format(ship.id, ship.position, ship.halite_amount, ship_status[ship.id]))

        if ship_status[ship.id] == "returning":
            if ship.position == me.shipyard.position:
                logging.info("Ship - Drop-off")
                ship_status[ship.id] = "exploring"
            else:
                dropoffs = me.get_dropoffs()
                destinations = list(dropoffs) + [me.shipyard.position]

                minDistance = False
                movePosition = False
                move = False

                logging.info("Game - destinations: {}".format(destinations))

                for dest in destinations:
                    distance = game_map.calculate_distance(ship.position, dest)
                    if minDistance == False or distance < minDistance:
                        minDistance = distance
                        movePosition = dest

                move =  Direction.convert(game_map.naive_navigate(ship, movePosition))

                logging.info("Ship - initial move1: {}".format(move))

                if move == "o":
                    logging.info("Ship - STUCK1")
                else:
                    fuelCost = round(game_map[ship.position].halite_amount * .1, 2)
                    if fuelCost > ship.halite_amount:
                        logging.info("Ship - insuffient fuel. Have {}, need {}".format(ship.halite_amount, fuelCost))
                        move = "o"

                command_queue.append(ship.move(move))
                continue

        elif ship.halite_amount >= constants.MAX_HALITE / 4:
            ship_status[ship.id] = "returning"

        if game_map[ship.position].halite_amount < constants.MAX_HALITE / 10 or ship.is_full:
            move = random.choice(["n", "s", "e", "w"])

            #logging.info("Ship - initial move2: {}".format(move))

            moveOffset = ship.position.directional_offset(DIRECTIONS[move])

            #logging.info("Ship - moveOffset2: {}".format(moveOffset))

            move = Direction.convert(game_map.naive_navigate(ship, moveOffset))

            #logging.info("Ship - final move2: {}".format(move))

            if move == "o":
                logging.info("Ship - STUCK2")
            else:
                fuelCost = round(game_map[ship.position].halite_amount * .1, 2)
                if fuelCost > ship.halite_amount:
                    logging.info("Ship - insuffient fuel. Have {}, need {}".format(ship.halite_amount, fuelCost))
                    move = "o"

            command_queue.append(ship.move(move))
        else:
            command_queue.append(ship.stay_still())

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if (nShips < 8 or game.turn_number <= 200) and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied:
        command_queue.append(me.shipyard.spawn())
        logging.info("Ship - Spawn")

    #logging.info("Game - commad queue: {}".format(command_queue))

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)

