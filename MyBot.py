#!/usr/bin/env python3
# Python 3.6

import hlt

from hlt import constants
from hlt.entity import Shipyard

import logging
import datetime
import math
import time
import numpy as np

from myutils.utils import *
from myutils.constants import *

#
# main
#

""" <<<Game Begin>>> """

game_start_time = time.time()

game = hlt.Game()

# keep ship state inbetween turns
ship_states = {}
botName = "MyBot.dev"
cumulative_profit = 5000
loiter_assignments = {}

#
#  value map
#

cell_value_map = game.game_map.get_cell_value_map(game.me.shipyard.position)

if DEBUG & (DEBUG_GAME): logging.info("Game - Initialization elapsed time: {}".format(round(time.time() - game_start_time, 2)))

#
# game start
#

game.ready(botName)

if DEBUG & (DEBUG_GAME): logging.info("Game - Successfully created bot! My Player ID is {}. {} ({})".format(game.my_id, "{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now()), round(time.time())))

""" <<<Game Loop>>> """

while True:
    turn_spent = 0
    turn_gathered = 0
    turn_profit = 0
    turn_start_time = time.time()

    game.update_frame()

    me = game.me
    game_map = game.game_map
    game_metrics = game.game_metrics

    command_queue = []

    #
    # Calc hotspots (loiter assignments) and dense areas
    #
    cell_value_map = game_map.get_cell_value_map(me.shipyard.position)

    if game.turn_number == 1:
		logging.debug("game {}".format(game))
        dump_data_file(game, cell_value_map, "cell_value_map")

    threshold = cell_value_map.max() * .5
    hottest_areas = np.ma.MaskedArray(cell_value_map, mask= [cell_value_map < threshold], fill_value = 0)

    row, col = hottest_areas.nonzero()

    #################### in later game esp. need to adjust mining threshold based on remaining halite

    hotspots = []
    for y, x in zip(row, col):
        p = Position(x, y)
        logging.debug("Hotspot: {}".format(p))
        hotspots.append((p, game_map[p].halite_amount))

    logging.debug("Pre-Hotspots: {}".format(hotspots))

    # remove the hotspots previosly assigned, but not reached
    hotspots[:] = [x for x in hotspots if x[0] not in loiter_assignments]

    logging.debug("Post-Hotspots: {}".format(hotspots))

    # sorted_blocks = sorted(moves, key=lambda item: item[2], reverse=True)
    targets = sorted(hotspots, key=lambda item: item[1])

    logging.debug("Targets: {}".format(targets))

    logging.debug("Loiter assignments: {}".format(loiter_assignments))

    if DEBUG & (DEBUG_GAME): logging.info("Game - Turn setup elapsed time: {}".format(round(time.time() - turn_start_time, 2)))

    #
    # initialize the ship states
    #

    my_ships = me.get_ships()

    for ship in my_ships:
        if ship.id in ship_states:

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
            if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} is a new ship".format(ship.id))
            me.ship_count += 1

            turn_spent = constants.SHIP_COST
            game_metrics["spent"].append((game.turn_number, turn_spent))

            ship_states[ship.id] = {
                "last_seen": game.turn_number,
                "prior_position": None,
                "prior_halite_amount": None,
                "status": "returning",
                "last_dock": game.turn_number,
                "christening": game.turn_number,
                "path": []
            }

            # we can't attach a christening attrib to the acutal ship obj because we'll lose
            # the info once the ship is destroyed. We're interested in destroyed ship info when
            # we calc stats such as mining rate
            game.ship_christenings[ship.id] = game.turn_number

        # attribs not dependent on save state
        ship.last_seen = game.turn_number

        # update the current ship based on saved state
        ship.status = ship_states[ship.id]["status"]
        ship.path = ship_states[ship.id]["path"]
        ship.christening = ship_states[ship.id]["christening"]
        ship.last_dock = ship_states[ship.id]["last_dock"]

        # note, some ship state attribs are not stored on the actual ship object:
        # prior_position, prior_halite_amount

    #
    # handle each ship for this turn
    #
    for ship in my_ships:
        dropoff_position = get_dropoff_position(game, ship)

        if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} at {} has {} halite and is {}".format(ship.id, ship.position, ship.halite_amount, ship.status))

        #
        # status - returning
        #
        if ship.status == "returning" or ship.position == dropoff_position:
            #
            # Returning
            #
            if ship.position == dropoff_position:
                dropoff_amount = ship_states[ship.id]["prior_halite_amount"]
                if not (dropoff_amount is None):
                    if DEBUG & (DEBUG_GAME): logging.info("GAME - Ship {} completed dropoff of {} halite at {}. Return took {} turns".format(ship.id, dropoff_amount, dropoff_position, game.turn_number - ship.last_dock))

                #ship.path.clear()

                # takes 6 turns to get the first 4 ships out, make this a special state/status?
                if game.turn_number <= 6:
                    cardinals = ["w", "n", "s", "e"]
                    hint = cardinals[me.ship_count % 4]
                    loiter_point = get_loiter_point(game, ship, hint)
                    departure_point = None
                else:
                    hint = None

                    if len(targets) != 0:
                        loiter_point = targets.pop()[0]
                        loiter_assignments[loiter_point] = ship.id
                        logging.info("GAME - Ship {} assigned loiter point {} off target list. {} targets remain".format(ship.id, loiter_point, len(targets)))
                    else:
                        loiter_point = get_loiter_point(game, ship, hint)
                        logging.info("GAME - Ship {} No targets remain, using random loiter point {}".format(ship.id, loiter_point))

                    departure_point = get_departure_point(dropoff_position, loiter_point)

                if departure_point is None:
                    path, cost = game_map.navigate(dropoff_position, loiter_point, "astar", {"move_cost": "turns"}) # heading out to loiter point
                else:
                    path, cost = game_map.navigate(departure_point, loiter_point, "astar", {"move_cost": "turns"}) # heading out to loiter point
                    path.append(departure_point)

                if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} has a departure point of {} for loiter point {}. Hint: {}".format(ship.id, departure_point, loiter_point, hint))

                if path is None:
                    ship.path = []
                    ship.status = "exploring"
                    logging.error("Ship {} Error, navigate failed for loiter point {}".format(ship.id, loiter_point))
                else:
                    ship.path = path
                    ship.status = "transiting"
                    if DEBUG & (DEBUG_NAV): logging.info("Ship - Ship {} is heading out to {}, ETA {} turns ({}).".format(ship.id, loiter_point, len(ship.path), round(cost)))
            else:
                #
                # Returning
                #

                # For a returning ship in transit, we don't need to do anything, the move
                # code will grab the next position/point and create a move for it
                if DEBUG & (DEBUG_NAV): logging.info("Ship - Ship {} is {} away from dropoff ({}). ETA {} turns.".format(ship.id, game_map.calculate_distance(ship.position, dropoff_position), dropoff_position, len(ship.path)))

        #
        # status exploring|transiting --> returning
        #
        elif ship.halite_amount >= constants.MAX_HALITE or ship.is_full:
            ship.status = "returning"

            if not (ship.halite_amount is None):
                game_metrics["return_duration"].append((game.turn_number, ship.id, game.turn_number - ship.last_dock))

            path, cost = game_map.navigate(ship.position, dropoff_position, "dock") # returning to shipyard/dropoff

            if path is None:
                if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} Error, navigate return None")
                ship.path = []
                logging.error("Ship {} Error, navigate failed for dropoff {}".format(ship.id, dropoff_position))
            else:
                ship.path = path
                if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} is now returning to {} at a cost of {} ({} turns)".format(ship.id, dropoff_position, round(cost, 1), len(ship.path)))

        #
        # status exploring|transiting
        #
        else:
            if len(ship.path) == 0:
                ship.status = "exploring"
                if ship.position in loiter_assignments:
                    loiter_assignments.pop(ship.position, None)

                if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} is now exploring".format(ship.id))
            else:
                ship.status = "transiting" # is this necessary ???


        #
        # Move
        #

        # if cell is below mining threshold then continue,
        # if the ship is above cargo threshold continue
        # else we'll stay in place and mine
        if should_move(game, ship):
            #
            # exploring (not mining)
            #
            # if we're already at out next position, pop it off we don't waste the turn - why is this happening?
            if len(ship.path) and ship.position == ship.path[len(ship.path) - 1]:
                logging.warning("Ship {} popped a useless point {}".format(ship.id, ship.path[len(ship.path) - 1]))
                ship.path.pop()

            if ship.status == "exploring":
                move = get_move(game, ship, "density")
                if DEBUG & (DEBUG_GAME): logging.info("GAME - Ship {} is exploring to the {}".format(ship.id, move))
            elif ship.status == "transiting" or ship.status == "returning":
                move = get_nav_move(game, ship, "astar", {"move_cost": "turns"}) # here the path scheme specifies the algo to use if we have an incomplete path
                if DEBUG & (DEBUG_GAME): logging.info("GAME - Ship {} is transiting {}".format(ship.id, move))
            else:
                move = get_move(game, ship, "density", "density")
                logging.error("Error - Ship {} should move, but has an unexpected status {}, falling back to density move {}".format(ship.id, ship.status, move))

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
        ship_states[ship.id]["christening"] = ship.christening
        ship_states[ship.id]["last_dock"] = ship.last_dock

    # check if we can spawn a ship
    if ships_are_spawnable(game):
        command_queue.append(me.shipyard.spawn())
        if DEBUG & (DEBUG_GAME): logging.info("Game - Ship spawn request")

    #
    # collenct game metrics
    #
    turn_profit = turn_gathered - turn_spent
    cumulative_profit += (turn_gathered - turn_spent)
    game_metrics["profit"].append((game.turn_number, turn_profit))
    game_metrics["time"].append((game.turn_number, round(time.time() - turn_start_time, 4)))

    #
    # debug info for each turn
    #

    # check of lost ships
    lost_ships = []
    for s_id in ship_states:
        if not me.has_ship(s_id):
            lost_ships.append(s_id)

    for s_id in lost_ships:
        if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} lost. Last seen on turn {}".format(s_id, ship_states[s_id]["last_seen"]))
        ship_states.pop(s_id, None)

    if DEBUG & (DEBUG_COMMANDS): logging.info("Game - command queue: {}".format(command_queue))

    if DEBUG & (DEBUG_SHIP_STATES): logging.info("Game - end ship_states: {}".format(ship_states))

    if DEBUG & (DEBUG_GAME_METRICS):
        mined_this_turn = sum(map(lambda i: i[2] if i[0] == game.turn_number else 0, game_metrics["mined"]))
        logging.info("Game - Mined this turn: {}".format(mined_this_turn))
        logging.info("Game - Mining rate: {}".format(round(get_mining_rate(game, 25), 2)))

    if DEBUG & (DEBUG_GAME_METRICS):
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
        logging.info("Game - Profit: {} {}".format(turn_profit, cumulative_profit))

    if DEBUG & (DEBUG_GAME_METRICS):
        mined_by_ship= {}
        avg_mined_by_ship = {}
        oldest_turn = 1 if game.turn_number < MINING_RATE_LOOKBACK else (game.turn_number - MINING_RATE_LOOKBACK)
        i = len(game.game_metrics["mined"]) - 1
        while i >= 0 and game.game_metrics["mined"][i][0] >= oldest_turn:
            s_id = game.game_metrics["mined"][i][1]
            halite = game.game_metrics["mined"][i][2]
            mined_by_ship[s_id] = (mined_by_ship[s_id] + halite) if s_id in mined_by_ship else halite
            i -= 1

        for s_id, halite in mined_by_ship.items():
            avg_mined_by_ship[s_id] = halite / (game.turn_number - game.ship_christenings[s_id] - 1)

        logging.info("Game - Ship mining rate averages (Last {} turns):".format(MINING_RATE_LOOKBACK))
        for s_id in avg_mined_by_ship:
            logging.info("Game - {:4d}: {}".format(s_id, round(avg_mined_by_ship[s_id], 2)))

        logging.info("Game - Ship yields (Last {} turns):".format(MINING_RATE_LOOKBACK))
        for s_id, halite in mined_by_ship.items():
            logging.info("Game - {:4d}: {}".format(s_id, halite))

    if DEBUG: logging.info("Game - Turn time: {}".format(round(time.time() - turn_start_time, 4)))

    #
    # last turn output
    #
    if game.turn_number == constants.MAX_TURNS:
        if DEBUG & (DEBUG_NAV_METRICS):
            logging.info("Nav - Loiter multiples: {}".format(game_metrics["loiter_multiples"]))
            logging.info("Nav - Loiter offsets: {}".format(game_metrics["loiter_offsets"]))
            logging.info("Nav - Loiter distances: {}".format(game_metrics["loiter_distances"])) # raw_loiter_point
            logging.info("Nav - Raw loiter points: {}".format(game_metrics["raw_loiter_points"]))

            avg_duration = 0 if len(game_metrics["return_duration"]) == 0 else np.mean(game_metrics["return_duration"][2], axis=0)
            logging.info("Game - Avg. ship return duration: {}".format(round(avg_duration, 2)))

        if DEBUG & (DEBUG_GAME_METRICS):
            logging.info("Game - Min turn time: {}".format(min(game_metrics["time"], key = lambda t: t[1])))
            logging.info("Game - Max turn time: {}".format(max(game_metrics["time"], key = lambda t: t[1])))
            logging.info("Game - Avg turn time: {:.4f}".format(np.mean(game_metrics["time"], axis=0)[1]))

        if DEBUG & (DEBUG_OUTPUT_GAME_METRICS):
            dump_stats(game, game_metrics, "all")

        if DEBUG & (DEBUG_GAME): logging.info("Game - Elapsed time: {}".format(round(time.time() - game_start_time, 2)))

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)


