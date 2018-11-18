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
import numpy as np

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

botName = "MyBot.dev"

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
    game_metrics = game.game_metrics

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    # end of the turn.
    command_queue = []

    #if DEBUG & (DEBUG_STATES): logging.info("Game - begin ship_states: {}".format(ship_states))

    for ship in me.get_ships():
        dropoff_position = get_dropoff_position(game, ship)

        #
        # initialize ship states
        #
        if ship.id in ship_states:
            ship.status = ship_states[ship.id]["status"]
            ship.path = ship_states[ship.id]["path"]

            if ship.halite_amount != ship_states[ship.id]["prior_halite_amount"]:
                if ship.halite_amount == 0:
                    fuel_cost = math.floor(game_map[ship_states[ship.id]["prior_position"]].halite_amount * .1)
                    gathered = ship_states[ship.id]["prior_halite_amount"] - fuel_cost
                    game_metrics["gathered"].append((game.turn_number, ship.id, gathered))
                elif ship.halite_amount < ship_states[ship.id]["prior_halite_amount"]:
                    fuel_cost = ship_states[ship.id]["prior_halite_amount"] - ship.halite_amount
                    game_metrics["burned"].append((game.turn_number, ship.id, fuel_cost))
                else:
                    mined = ship.halite_amount - ship_states[ship.id]["prior_halite_amount"]
                    game_metrics["mined"].append((game.turn_number, ship.id, mined))
        else:
            if DEBUG & (DEBUG_GAME): logging.info("Game - New ship with ID {}".format(ship.id))

            ship_states[ship.id] = {
                "status": "exploring",
                "path": []
            }

            ship.status = ship_states[ship.id]["status"]
            ship.path = ship_states[ship.id]["path"]

        if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} at {} has {} halite and is {}".format(ship.id, ship.position, ship.halite_amount, ship.status))

        #
        # status - returning
        #
        if ship.status == "returning":
            if ship.position == dropoff_position:
                if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} completed Dropoff of {} halite at {}".format(ship.id, ship_states[ship.id]["prior_halite_amount"], dropoff_position))

                # Returning - at dropoff:
                #
                # 1. get the loiter distance (multiplier)
                # 2. get a random point on a circle an mult by the loiter multiple
                # 3. extend the circle x,y by the loiter distance to create an offset
                # 4. Add the offset to the current position to get the loiter point
                # 5. Calc a nav path to the loiter point

                loiter_distance = get_loiter_multiple(game)

                if DEBUG & (DEBUG_NAV): logging.info("NAV - Ship {} loiter_distance: {}".format(ship.id, loiter_distance))

                if DEBUG & (DEBUG_NAV_METRICS): debug_metrics["loiter_multiples"].append((game.turn_number, round(loiter_distance, 2)))

                # get a random point on a cicle
                randPi = random.random() * math.pi * 2
                raw_loiter_point = (math.cos(randPi), math.sin(randPi))
                loiterOffset = Position(round(raw_loiter_point[0] * loiter_distance), round(raw_loiter_point[1] * loiter_distance))

                if DEBUG & (DEBUG_NAV_METRICS): debug_metrics["loiter_offsets"].append((loiterOffset.x, loiterOffset.y))
                if DEBUG & (DEBUG_NAV_METRICS): debug_metrics["loiter_distances"].append((game.turn_number, round(math.sqrt(loiterOffset.x ** 2 + loiterOffset.y ** 2), 2)))

                loiterPoint = ship.position + loiterOffset

                ship.path.clear()
                ship.path, cost = game_map.navigate(ship, loiterPoint, "turns")
                if DEBUG & (DEBUG_NAV): logging.info("Ship - Ship {} is heading out to {}, ETA {} turns ({}).".format(ship.id, loiterPoint, len(ship.path), cost))
                ship.status = "exploring"
            else:
                #
                # Returning - in transit
                #
                # For a returning ship in transit, we don't need to do anything, the move
                # code will  grab the next position/point and create a move for it
                if DEBUG & (DEBUG_NAV): logging.info("Ship - Ship {} returning and is {} moves out".format(ship.id, len(ship.path)))

#                if move == "o":
#                    if DEBUG & (DEBUG_NAV): logging.info("Ship - Ship {} Collision returning".format(ship.id))
#                    ship.status = "backingoff"
#                    bop = get_backoff_point(game, ship, dropoff_position)
#                    logging.info("DEBUG - Ship {} bop: {}".format(ship.id, bop))
#                    ship.path.append(bop)




        #
        # status - backing off
        #
        elif ship.status == "backingoff":

            # a ship is backing off when collides during return.  Backoff involves reversing direction
            # for a random number of moves toword a backoff point. Once the backoff point is reached, the
            # ship will return to a 'returning' status
            if len(ship.path) == 0:
                ship.status = "returning"
                ship.path.append(dropoff_position) # complet path will be calc'd by get_move if the distance to dropoff_position is > 1
                if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} backoff is complete to {}".format(ship.id, ship.position))
            else:
                if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} is backing off to {}".format(ship.id, ship.path[0]))

        #
        # status - ship full
        #
        elif ship.halite_amount >= constants.MAX_HALITE or ship.is_full:
            ship.status = "returning"
            ship.path, cost = game_map.navigate(ship, dropoff_position, "halite")
            if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} is now returning to {} at a cost of {}".format(ship.id, dropoff_position, cost))

        #
        # Move
        #
        # if the cell we're on is essentially empty or the ship is full, continue on ...
        # else we'll stay in place and mine
        if game_map[ship.position].halite_amount < constants.MAX_HALITE / 10 or ship.is_full:

            #
            # exploring (not mining)
            #
            # if we're already at out next position, pop it off we don't waste the turn
            if len(ship.path) and ship.position == ship.path[len(ship.path) - 1]:
                ship.path.pop()

            if len(ship.path) == 0:
                move = get_density_move(game, ship)
            else:
                move = get_ship_nav_move(game, ship)

            if DEBUG & (DEBUG_NAV): logging.info("Ship - Ship {} is moving {}".format(ship.id, move))

            command_queue.append(ship.move(move))
        else:

            #
            # mining
            #
            command_queue.append(ship.stay_still())

        #
        # save the ship state
        #
        ship_states[ship.id]["status"] = ship.status
        ship_states[ship.id]["path"] = ship.path
        ship_states[ship.id]["prior_position"] = ship.position
        ship_states[ship.id]["prior_halite_amount"] = ship.halite_amount

    #
    #
    #
    if spawn_ship(game):
        command_queue.append(me.shipyard.spawn())
        if DEBUG & (DEBUG_GAME): logging.info("Game - Ship spawn")

    if DEBUG & (DEBUG_COMMANDS): logging.info("Game - command queue: {}".format(command_queue))

    if DEBUG & (DEBUG_STATES): logging.info("Game - end ship_states: {}".format(ship_states))

    if game.turn_number == constants.MAX_TURNS:
        if DEBUG & (DEBUG_GAME_METRICS):
            #logging.info("Game - Time: {}".format(game_metrics["time"]))
            logging.info("Game - Min turn time: {}".format(min(game_metrics["time"], key = lambda t: t[1])))
            logging.info("Game - Max turn time: {}".format(max(game_metrics["time"], key = lambda t: t[1])))
            logging.info("Game - Avg turn time: {:.4f}".format(np.mean(game_metrics["time"], axis=0)[1]))

            #logging.info("Game - Mined: {}".format(game_metrics["mined"]))
            logging.info("Game - Total mined: {}".format(sum(x[2] for x in game_metrics["mined"])))

            #logging.info("Game - Gathered: {}".format(game_metrics["gathered"]))
            logging.info("Game - Total gathered: {}".format(sum(x[2] for x in game_metrics["gathered"])))

            #logging.info("Game - Burned: {}".format(game_metrics["burned"]))
            logging.info("Game - Total burned: {}".format(sum(x[2] for x in game_metrics["burned"])))

        if DEBUG & (DEBUG_NAV_METRICS):
            logging.info("Nav - Loiter multiples: {}".format(debug_metrics["loiter_multiples"]))
            logging.info("Nav - Loiter offsets: {}".format(debug_metrics["loiter_offsets"]))
            logging.info("Nav - Loiter distances: {}".format(debug_metrics["loiter_distances"]))

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)

    if DEBUG & (DEBUG_GAME_METRICS): game_metrics["time"].append((game.turn_number, round(time.time() - TurnStartTime, 4)))
