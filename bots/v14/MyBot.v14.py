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

botName = "MyBot.v14"
#
# game start
#

game.ready(botName)

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
# Here, you log here your id, which you can always fetch from the game object by using my_id.
if DEBUG & (DEBUG_GAME): logging.info("Game - Successfully created bot! My Player ID is {}. {}".format(game.my_id, "{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now())))

""" <<<Game Loop>>> """

while True:
    turn_spent = 0
    turn_gathered = 0
    turn_start_time = time.time()

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

    my_ships = me.get_ships()

    #
    # initialize the ship states
    #
    for ship in my_ships:
        if ship.id in ship_states:
            ship.status = ship_states[ship.id]["status"]
            ship.path = ship_states[ship.id]["path"]
            ship.last_seen = game.turn_number

            # we calc mined amount and fuel cost based on the diff of what we had
            # last turn and what the server says we have now
            if ship.halite_amount != ship_states[ship.id]["prior_halite_amount"]:
                if ship.halite_amount == 0:
                    fuel_cost = math.floor(game_map[ship_states[ship.id]["prior_position"]].halite_amount * .1)
                    gathered = ship_states[ship.id]["prior_halite_amount"] - fuel_cost
                    turn_gathered += gathered
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
                "last_seen": game.turn_number,
                "prior_position": None,
                "prior_halite_amount": None,
                "status": "returning",
                "path": []
            }

            ship.status = ship_states[ship.id]["status"]
            ship.path = ship_states[ship.id]["path"]
            ship.last_seen = game.turn_number

    #
    # handle each ship for this turn
    #
    for ship in my_ships:
        dropoff_position = get_dropoff_position(game, ship)

        if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} at {} has {} halite and is {}".format(ship.id, ship.position, ship.halite_amount, ship.status))

        #
        # status - returning
        #
        if ship.status == "returning":
            #
            # Returning - in transit
            #
            if ship.position == dropoff_position:
                if DEBUG & (DEBUG_GAME): logging.info("GAME - Ship {} completed Dropoff of {} halite at {}".format(ship.id, ship_states[ship.id]["prior_halite_amount"], dropoff_position))

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
                path, cost = game_map.navigate(ship, loiterPoint, "astar", {"move_cost": "turns"}) # heading out to loiter point

                if path == None:
                    if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} Error, navigate return None")
                    ship.path = []
                    logging.warning("Ship {} Error, navigate failed for loiter point {}".format(ship.id, loiterPoint))
                else:
                    ship.path = path
                    if DEBUG & (DEBUG_NAV): logging.info("Ship - Ship {} is heading out to {}, ETA {} turns ({}).".format(ship.id, loiterPoint, len(ship.path), round(cost)))

                ship.status = "exploring"
            else:
                #
                # Returning - in transit
                #
                # For a returning ship in transit, we don't need to do anything, the move
                # code will grab the next position/point and create a move for it
                if DEBUG & (DEBUG_NAV): logging.info("Ship - Ship {} is {} away from dropoff ({}). ETA {} turns.".format(ship.id, len(ship.path), dropoff_position, len(ship.path)))

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
            path, cost = game_map.navigate(ship, dropoff_position, "astar", {"move_cost": "turns"}) # returning to shipyard/dropoff

            if path == None:
                if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} Error, navigate return None")
                ship.path = []
                logging.warning("Ship {} Error, navigate failed for dropoff {}".format(ship.id, dropoff_position))
            else:
                ship.path = path
                if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} is now returning to {} at a cost of {} ({} turns)".format(ship.id, dropoff_position, round(cost, 1), len(ship.path)))

        #
        # Move
        #

        # if cell is essentially empty then continue, if the ship is full continue
        # else we'll stay in place and mine
        if should_move(game, ship):
            #
            # exploring (not mining)
            #
            # if we're already at out next position, pop it off we don't waste the turn
            if len(ship.path) and ship.position == ship.path[len(ship.path) - 1]:
                logging.warning("Ship {} popped a useless point {}".format(ship.id, ship.path[len(ship.path) - 1]))
                ship.path.pop()

            if len(ship.path) == 0:
                move = get_move(game, ship, "density")
                if DEBUG & (DEBUG_GAME): logging.info("GAME - Ship {} is exploring to the {}".format(ship.id, move))
            else:
                # here, the path scheme specifies the algo to use if we have an incomplete path
                move = get_ship_nav_move(game, ship, "astar", {"move_cost": "turns"})
                if DEBUG & (DEBUG_GAME): logging.info("GAME - Ship {} is transiting {}".format(ship.id, move))

            command_queue.append(ship.move(move))
        else:
            #
            # mining
            #
            if DEBUG & (DEBUG_GAME): logging.info("GAME - Ship {} is mining".format(ship.id))
            command_queue.append(ship.stay_still())

        #
        # save the ship state
        #
        ship_states[ship.id]["status"] = ship.status
        ship_states[ship.id]["path"] = ship.path
        ship_states[ship.id]["prior_position"] = ship.position
        ship_states[ship.id]["prior_halite_amount"] = ship.halite_amount
        ship_states[ship.id]["last_seen"] = ship.last_seen

    # check of lost ships
    for ship_id in ship_states:
        if not me.has_ship(ship_id):
            if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} lost. Last seen on turn {}".format(ship_id, ship_states[ship_id]["last_seen"]))

    # check if we can spawn a ship
    if spawn_ship(game):
        command_queue.append(me.shipyard.spawn())
        turn_spent = constants.SHIP_COST
        game_metrics["spent"].append((game.turn_number, turn_spent))
        if DEBUG & (DEBUG_GAME): logging.info("Game - Ship spawn")

    if DEBUG & (DEBUG_COMMANDS): logging.info("Game - command queue: {}".format(command_queue))

    if DEBUG & (DEBUG_STATES): logging.info("Game - end ship_states: {}".format(ship_states))

    game_metrics["profit"].append((game.turn_number, turn_gathered - turn_spent))

    # dump metrics on last turn, if we do this after the game loop it'll never happen since
    # the game shuts down immediately after the last turn
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

            # profit = gathered - spent
            logging.info("Game - Profit: {}".format(sum(x[1] for x in game_metrics["profit"])))

        if DEBUG & (DEBUG_NAV_METRICS):
            logging.info("Nav - Loiter multiples: {}".format(debug_metrics["loiter_multiples"]))
            logging.info("Nav - Loiter offsets: {}".format(debug_metrics["loiter_offsets"]))
            logging.info("Nav - Loiter distances: {}".format(debug_metrics["loiter_distances"]))

        if DEBUG & (DEBUG_OUTPUT_GAME_METRICS):
            dump_stats(game, game_metrics, "all")

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)

    if DEBUG & (DEBUG_GAME_METRICS): game_metrics["time"].append((game.turn_number, round(time.time() - turn_start_time, 4)))
