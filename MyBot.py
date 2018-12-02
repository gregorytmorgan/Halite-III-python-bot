#!/usr/bin/env python3
# Python 3.6

import hlt

from hlt import constants

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
ship_states = {} # keep ship state inbetween turns
botName = "MyBot.dev"
cumulative_profit = 5000
loiter_assignments = {}

#
#  value map
#

cell_value_map = game.game_map.get_cell_value_map(game.me.shipyard.position)

if DEBUG & (DEBUG_TIMING): logging.info("Game - Initialization elapsed time: {}".format(round(time.time() - game_start_time, 2)))

#
# game start
#

game.ready(botName)

if DEBUG & (DEBUG_TIMING): logging.info("Game - Successfully created bot! My Player ID is {}. {} ({})".format(game.my_id, "{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now()), round(time.time())))

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

    cell_values = game_map.get_halite_map()
    cell_values_flat = cell_values.flatten()

#    if game.turn_number < 10 or game.turn_number > constants.MAX_TURNS - 4:
#        np.set_printoptions(precision=1, linewidth=240, floatmode="fixed", suppress=True, threshold=np.inf)
#        logging.debug("cell_values:\n{}".format(cell_values.astype(np.int)))
#    else:
#        np.set_printoptions(precision=1, linewidth=240, floatmode="fixed", suppress=True, threshold=25)
#
#    logging.debug("cell_values shape: {}".format(cell_values_flat.shape))
#    logging.debug("cell_values amax: {}".format(np.amax(cell_values_flat)))
#    logging.debug("cell_values mean: {}".format(cell_values_flat.mean()))
#    logging.debug("cell_values mode: {}".format(stats.mode(cell_values_flat)[0][0]))

    cell_values_flat.sort()

    # when mean == mode, then evenly distributed
#    cnt = cell_values_flat.shape[0]
#    logging.debug("1/5:{} 4/5:{}".format(cell_values_flat[round(cnt/5.0)], cell_values_flat[round(cnt*4.0/5.0)]))

    #
    # Calc hotspots (loiter assignments) and dense areas
    #
    if USE_CELL_VALUE_MAP:
        cell_value_map = game_map.get_cell_value_map(me.shipyard.position, game.get_mining_rate(MINING_RATE_LOOKBACK))

#        if game.turn_number < 10 or game.turn_number > constants.MAX_TURNS - 4:
#            np.set_printoptions(precision=1, linewidth=240, floatmode="fixed", suppress=True, threshold=np.inf)
#            logging.debug("cell_values:\n{}".format(cell_value_map.astype(np.int)))
#        else:
#            np.set_printoptions(precision=1, linewidth=240, floatmode="fixed", suppress=True, threshold=25)

        if game.turn_number == 1 or game.turn_number == round(constants.MAX_TURNS/2) or game.turn_number == constants.MAX_TURNS:
            dump_data_file(game, cell_value_map, "cell_value_map_turn_" + str(game.turn_number))

        threshold = cell_value_map.max() * .5

        hottest_areas = np.ma.MaskedArray(cell_value_map, mask= [cell_value_map < threshold], fill_value = 0)

        y_vals, x_vals = hottest_areas.nonzero()

        # late game we need to adjust mining threshold based on remaining halite to pickup cells
        # less halite than the existing threshold

        hotspots = []
        for x, y in zip(x_vals, y_vals):
            p = Position(x, y)
            hotspots.append((p, cell_value_map[y][x], game_map[p].halite_amount)) # (position, value, halite)

        # remove the hotspots previosly assigned, but not reached
        hotspots[:] = [x for x in hotspots if x[0] not in loiter_assignments]

        targets = sorted(hotspots, key=lambda item: item[1])
    else:
        targets = []

#    logging.debug("Targets: {}".format(targets))
#    logging.debug("Loiter assignments: {}".format(loiter_assignments))

    if DEBUG & (DEBUG_TIMING): logging.info("Game - Turn setup elapsed time: {}".format(round(time.time() - turn_start_time, 2)))

    #
    # initialize the ship states
    #

    my_ships = me.get_ships()

    # sort the ships by halite, this helps give returning ships priority/helps with
    # traffic issues around dropoffs until better collision mgmt is in place
    my_ships.sort(key = lambda s: s.halite_amount, reverse = True)

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
        # e.g. prior_position, prior_halite_amount

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
            # Returning - arrived
            if ship.position == dropoff_position:
                dropoff_amount = ship_states[ship.id]["prior_halite_amount"]
                if not (dropoff_amount is None):
                    if DEBUG & (DEBUG_GAME): logging.info("GAME - Ship {} completed dropoff of {} halite at {}. Return took {} turns".format(ship.id, dropoff_amount, dropoff_position, game.turn_number - ship.last_dock))

                ship.path.clear() # may not have completed the previous path

                # takes 6 turns to get the first 4 ships out, make this a special state/status?
                if EXPEDITED_DEPARTURE and game.turn_number <= 6:
                    cardinals = ["w", "n", "s", "e"]
                    hint = cardinals[me.ship_count % 4]
                    loiter_point = get_loiter_point(game, ship, hint)
                    departure_point = ship.position.directional_offset(DIRECTIONS[hint])
                else:
                    hint = None

                    if len(targets) != 0:
                        loiter_point = targets.pop()[0]
                        loiter_assignments[loiter_point] = ship.id
                        if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} assigned loiter point {} off target list. {} targets remain".format(ship.id, loiter_point, len(targets)))
                    else:
                        loiter_point = get_loiter_point(game, ship, hint)
                        if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} No targets remain, using random loiter point {}".format(ship.id, loiter_point))

                    departure_point = get_departure_point(game, dropoff_position, loiter_point)

                path, cost = game_map.navigate(departure_point, loiter_point, "astar", {"move_cost": "turns"}) # heading out to loiter point
                path.append(departure_point)

                if DEBUG & (DEBUG_NAV_METRICS): game.game_metrics["loiter_distances"].append((game.turn_number, round(math.sqrt(abs(ship.position.x - loiter_point.x) ** 2 + abs(ship.position.y - loiter_point.y) ** 2), 2)))
                if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} has a departure point of {} for loiter point {}. Hint: {}".format(ship.id, departure_point, loiter_point, hint))

                if path is None:
                    ship.path = []
                    ship.status = "exploring"
                    logging.error("Ship {} Error, navigate failed for loiter point {}".format(ship.id, loiter_point))
                else:
                    ship.path = path
                    ship.status = "transiting"
                    if DEBUG & (DEBUG_NAV): logging.info("Ship - Ship {} is heading out to {}, ETA {} turns ({}).".format(ship.id, loiter_point, game_map.calculate_distance(ship.position, dropoff_position), round(cost)))
            else:
                # status Returning - in transit
                #
                # For a returning ship in transit, we don't need to do anything, the move
                # code will grab the next position/point and create a move for it
                if DEBUG & (DEBUG_NAV): logging.info("Ship - Ship {} is {} away from dropoff ({}). ETA {} turns.".format(ship.id, game_map.calculate_distance(ship.position, dropoff_position), dropoff_position, len(ship.path)))

        #
        # status exploring|transiting --> returning
        #
        elif ship.halite_amount >= constants.MAX_HALITE or ship.is_full:
            ship.status = "returning"

            unassigned_pt = False
            for p, s in loiter_assignments.items():
                if s == ship.id:
                    unassigned_pt = p
                    if DEBUG & (DEBUG_GAME): logging.info("Ship - Ship {} didn't make it to loiter assignment {}, popped assignment".format(ship.id, p))
                    break

            if unassigned_pt:
                loiter_assignments.pop(unassigned_pt, None)

            if not (ship.halite_amount is None):
                game_metrics["return_duration"].append((game.turn_number, ship.id, game.turn_number - ship.last_dock))

            path, cost = game_map.navigate(ship.position, dropoff_position, "dock") # returning to shipyard/dropoff

            if path is None:
                if DEBUG & (DEBUG_NAV): logging.info("NAV - Ship {} Error, navigate return None")
                ship.path = []
                logging.error("Ship {} Error, navigate failed for dropoff {}".format(ship.id, dropoff_position))
            else:
                ship.path = path
                if DEBUG & (DEBUG_NAV): logging.info("NAV - Ship {} is now returning to {} at a cost of {} ({} turns)".format(ship.id, dropoff_position, round(cost, 1), len(ship.path)))

        #
        # status exploring|transiting (exploring when ship.path != 0)
        #
        else:
            if len(ship.path) == 0:
                ship.status = "exploring"
                if ship.position in loiter_assignments:
                    loiter_assignments.pop(ship.position, None)
                    if DEBUG & (DEBUG_GAME): logging.info("Ship - Ship {} reached loiter assignment {}, popped assignment".format(ship.id, ship.position))

                if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} is now exploring".format(ship.id))
            else:
                ship.status = "transiting"

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
            elif ship.status == "transiting":
                args = {
                    "waypoint_algorithm": "astar",
                    "move_cost": "turns"
                }
                move = get_move(game, ship, "nav", args) # path scheme = algo for incomplete path
                if DEBUG & (DEBUG_GAME): logging.info("GAME - Ship {} is {} {}".format(ship.id, ship.status, move))
            elif ship.status == "returning":
                move = get_move(game, ship, "nav", "naive") # returning will break if a waypoint resolution other than naive is used
                if DEBUG & (DEBUG_GAME): logging.info("GAME - Ship {} is {} {}".format(ship.id, ship.status, move))
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
    if spawn_ok(game):
        command_queue.append(me.shipyard.spawn())
        if DEBUG & (DEBUG_GAME): logging.info("Game - Ship spawn request")

    #
    # collenct game metrics
    #
    turn_profit = turn_gathered - turn_spent
    cumulative_profit += (turn_gathered - turn_spent)
    game_metrics["profit"].append((game.turn_number, turn_profit))
    game_metrics["turn_time"].append((game.turn_number, round(time.time() - turn_start_time, 4)))

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
        logging.info("Game - Mining rate: {}".format(round(game.get_mining_rate(MINING_RATE_LOOKBACK), 2)))

    if DEBUG & (DEBUG_TIMING):
        logging.info("Game - Min turn time: {}".format(min(game_metrics["turn_time"], key = lambda t: t[1])))
        logging.info("Game - Max turn time: {}".format(max(game_metrics["turn_time"], key = lambda t: t[1])))
        logging.info("Game - Avg turn time: {:.4f}".format(np.mean(game_metrics["turn_time"], axis=0)[1]))

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

    if DEBUG & (DEBUG_TIMING): logging.info("Game - Turn time: {}".format(round(time.time() - turn_start_time, 4)))

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

        if DEBUG & (DEBUG_TIMING):
            logging.info("Game - Min turn time: {}".format(min(game_metrics["turn_time"], key = lambda t: t[1])))
            logging.info("Game - Max turn time: {}".format(max(game_metrics["turn_time"], key = lambda t: t[1])))
            logging.info("Game - Avg turn time: {:.4f}".format(np.mean(game_metrics["turn_time"], axis=0)[1]))

        if DEBUG & (DEBUG_OUTPUT_GAME_METRICS):
            dump_stats(game, game_metrics, "all")

        if DEBUG & (DEBUG_TIMING): logging.info("Game - Elapsed time: {}".format(round(time.time() - game_start_time, 2)))

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)


