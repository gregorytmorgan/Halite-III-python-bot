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
# (print statements) are reserved for the engine-bot communication.
import logging
import datetime
import math
import time

# mybot code
from myutils.utils import *
from myutils.constants import *

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

botName = "MyBot.v12"

# modified after submit to halite.io -gtm
DebugMetrics = {
	"NavMults": [],
	"loiterOffsets": [],
	"loiterDistances": []
}

#
# game start
#

game.ready(botName)

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
# Here, you log here your id, which you can always fetch from the game object by using my_id.
if DEBUG & (DEBUG_GAME): logging.info("Game - Successfully created bot! My Player ID is {}. {}".format(game.my_id, "{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now())))

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
            if DEBUG & (DEBUG_GAME): logging.info("Game - New ship with ID {}".format(ship.id))
            ship_states[ship.id] = {
                "status": "exploring",
                "path": []
            }
            ship.status = ship_states[ship.id]["status"]
            ship.path = ship_states[ship.id]["path"]

        if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} at {} has {} halite and is {}".format(ship.id, ship.position, ship.halite_amount, ship.status))

        # state - returning
        if ship.status == "returning":
            ### TODO drop loc should be updated to handle dropoffs points
            if ship.position == me.shipyard.position:
                logging.info("Ship - Ship {} completed a Dropoff".format(ship.id))
                ship.path.clear()

                # 1. get the max loiter distance
                # 2. get the loiter multiple based on turn and max/min loiter distance
                # 3. get a random point on a circle an mult by the loiter multiple
                # 4. add the result to the current postion to get a destination

                loiterMult = get_loiter_multiple(game)
                if DEBUG & (DEBUG_NAV_METRICS): logging.info("NAV - Ship {} loiterMult: {}".format(ship.id, loiterMult))

                # Debug metric
                DebugMetrics["NavMults"].append((game.turn_number, round(loiterMult, 2)))

                #max_loiter_distance = get_max_loiter_distance(game)

                # get a random point on a cicle
                randPi = random.random() * math.pi * 2
                raw_loiter_point = (math.cos(randPi), math.sin(randPi))
                loiterOffset = Position(round(raw_loiter_point[0] * loiterMult), round(raw_loiter_point[1] * loiterMult))

                if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} loiterOffset: {}".format(ship.id, loiterOffset))

                # Debug metric, can't use position because will be for diff ship/position every time
                if DEBUG & (DEBUG_NAV_METRICS): DebugMetrics["loiterOffsets"].append((loiterOffset.x, loiterOffset.y))
                if DEBUG & (DEBUG_NAV_METRICS): DebugMetrics["loiterDistances"].append((game.turn_number, round(math.sqrt(loiterOffset.x ** 2 + loiterOffset.y ** 2), 2)))

                loiterPoint = ship.position + loiterOffset

                #logging.info("Ship - backoff/loiter point: {}".format(loiterPoint))

                ship.path.append(loiterPoint)

                ship.status = "exploring"
            else:
                dropoff_position = get_dropoff_position(game, ship)

                move = Direction.convert(game_map.naive_navigate(ship, dropoff_position))

                if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} initial move1: {}".format(ship.id, move))

                if move == "o":
                    if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} Collision returning".format(ship.id))
                    ship.status = "backingoff"
                    ship.path.append(get_backoff_point(game, ship, dropoff_position))
                else:
                    fuelCost = round(game_map[ship.position].halite_amount * .1, 2)
                    if fuelCost > ship.halite_amount:
                        if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} has insuffient fuel. Have {}, need {}".format(ship.id, ship.halite_amount, fuelCost))
                        move = "o"

                command_queue.append(ship.move(move))

                # save the ship state
                ship_states[ship.id]["status"] = ship.status
                ship_states[ship.id]["path"] = ship.path

                continue

        # state - backoff
        elif ship.status == "backingoff":
            if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} is backing off to {}".format(ship.id, ship.path[len(ship.path) - 1]))
            backoff_position = ship.path[len(ship.path) - 1]
            if ship.position == backoff_position:
                if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} backing off is complete at {}".format(ship.id, backoff_position))
                ship.status = "returning"
                ship.path.pop()
                ship.path.append(get_dropoff_position(game, ship))

        # state - exploring / state change
        elif ship.halite_amount >= constants.MAX_HALITE:
            if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} is now returning".format(ship.id))
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

            # if we don't have a nav path, then make a dense move, otherwise make a nav move.
            # In the case of a nav move, if collision, then just get a one-time random move
            if len(ship.path) == 0:
                if ship.is_full:
                    move = game_map.naive_navigate(ship, get_dropoff_position(game, ship))
                else:
                    move = get_dense_move(game, ship)
                    if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} dense_move: {}".format(ship.id, move))
            else:
                move = Direction.convert(game_map.naive_navigate(ship, ship.path[len(ship.path) - 1]))
                if move == "o":
                    original_move = move
                    move = get_dense_move(game, ship)
                    if move == "o":
                        if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} Nav move collision, original {}, correct failed.".format(ship.id, original_move))
                    else:
                        if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} Nav move collision, original {}, corrected {}".format(ship.id, original_move, move))

                if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} Move: {}".format(ship.id, move))

            if move != "o":
                fuelCost = round(game_map[ship.position].halite_amount * .1, 2)
                if fuelCost > ship.halite_amount:
                    if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} has insuffient fuel. Have {}, need {}".format(ship.id, ship.halite_amount, fuelCost))
                    move = "o"

            command_queue.append(ship.move(move))
        else:
            command_queue.append(ship.stay_still())

        # save the ship state
        ship_states[ship.id]["status"] = ship.status
        ship_states[ship.id]["path"] = ship.path

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if spawn_ship(game, 12):
        command_queue.append(me.shipyard.spawn())
        if DEBUG & (DEBUG_GAME): logging.info("Game - Ship spawn")

    #if DEBUG & (DEBUG_GAME): logging.info("Game - command queue: {}".format(command_queue))

    if DEBUG & (DEBUG_GAME): logging.info("Game - end ship_states: {}".format(ship_states))

    if DEBUG & (DEBUG_NAV_METRICS):
        if game.turn_number == constants.MAX_TURNS:
            logging.info("Nav - NavMults: {}".format(DebugMetrics["NavMults"]))
            logging.info("Nav - loiterOffsets: {}".format(DebugMetrics["loiterOffsets"]))
            logging.info("Nav - loiterDistances: {}".format(DebugMetrics["loiterDistances"]))

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)

    if DEBUG & (DEBUG_GAME): logging.info("elapsed turn time: {:.4f}".format(time.time() - TurnStartTime))
