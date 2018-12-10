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
botName = "MyBot.v21"
cumulative_profit = 5000

if DEBUG & (DEBUG_TIMING): logging.info("Time - Initialization elapsed time: {}".format(round(time.time() - game_start_time, 2)))

#
# game start
#

game.ready(botName)

if DEBUG & (DEBUG_GAME): logging.info("Game - Successfully created bot! My Player ID is {}. {} ({})".format(game.my_id, "{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now()), round(time.time())))

""" <<<Game Loop>>> """

while True:
    game.collisions.clear()
    game.command_queue = {}
    turn_spent = 0
    turn_gathered = 0
    turn_profit = 0
    turn_start_time = time.time()
    targets = []

    # convenience vars
    me = game.me
    game_map = game.game_map
    game_metrics = game.game_metrics

    game.update_frame()

    my_ships = me.get_ships()
    untasked_ships_cnt = len(my_ships) - len(game.loiter_assignments)

#    cell_values = game_map.get_halite_map()
#    cell_values_flat = cell_values.flatten()
#
#    if (game.turn_number > 1 and game.turn_number < 4) or game.turn_number > constants.MAX_TURNS - 4:
#        np.set_printoptions(precision=1, linewidth=240, floatmode="fixed", suppress=True, threshold=np.inf)
#        logging.debug("cell_values:\n{}".format(cell_values.astype(np.int)))
#    else:
#        np.set_printoptions(precision=1, linewidth=240, floatmode="fixed", suppress=True, threshold=25)
#
#    logging.debug("cell_values shape: {}".format(cell_values_flat.shape))
#    logging.debug("cell_values amax: {}".format(np.amax(cell_values_flat)))
#    logging.debug("cell_values mean: {}".format(cell_values_flat.mean()))
#    logging.debug("cell_values mode: {}".format(stats.mode(cell_values_flat)[0][0]))
#
#    cell_values_flat.sort()
#
#    # when mean == mode, then evenly distributed
#    cnt = cell_values_flat.shape[0]
#    logging.debug("1/5:{} 4/5:{}".format(cell_values_flat[round(cnt/5.0)], cell_values_flat[round(cnt*4.0/5.0)]))

    #
    # Calc hotspots (loiter assignments) and dense areas
    #
    if USE_CELL_VALUE_MAP:
        cell_value_map = game_map.get_cell_value_map(me.shipyard.position, 2 * game.get_mining_rate(MINING_RATE_LOOKBACK))

        if cell_value_map is None:
            raise RuntimeError("cv map is None")

        if DEBUG & (DEBUG_CV_MAP):
            if game.turn_number < 25 or game.turn_number > constants.MAX_TURNS - 1:
                np.set_printoptions(precision=1, linewidth=240, suppress=True, threshold=np.inf)
                logging.info("cell_values:\n{}".format(cell_value_map.astype(np.int)))
            else:
                np.set_printoptions(precision=1, linewidth=240, suppress=True, threshold=64)

        if DEBUG & (DEBUG_OUTPUT_GAME_METRICS):
            if game.turn_number in [1, round(constants.MAX_TURNS/2), constants.MAX_TURNS, 5, 10]:
                dump_data_file(game, cell_value_map, "cell_value_map_turn_" + str(game.turn_number))

        threshold = TARGET_THRESHOLD_DEFAULT

        while len(targets) < untasked_ships_cnt:

            if DEBUG & (DEBUG_GAME):
                if threshold == TARGET_THRESHOLD_DEFAULT:
                    logging.info("Game - Generating targets, threshold: {}".format(threshold))
                else:
                    logging.info("Game - Untasked ships({}) exceeds available targets({}), Generating targets, threshold: {}".format(untasked_ships_cnt, targets, threshold))

            hottest_areas = np.ma.MaskedArray(cell_value_map, mask = [cell_value_map <= threshold], fill_value = 0, copy=False)

#            if game.turn_number < 999 or game.turn_number > constants.MAX_TURNS - 1:
#                np.set_printoptions(precision=1, linewidth=240, suppress=True, threshold=np.inf)
#                np.ma.masked_print_option.set_display("---")
#                logging.debug("hottest_areas:\n{}".format(hottest_areas.astype(np.int)))

            y_vals, x_vals = hottest_areas.nonzero()

            hotspots = []
            for x, y in zip(x_vals, y_vals):
                p = Position(x, y)
                hotspots.append((p, round(cell_value_map[y][x]), game_map[p].halite_amount)) # (position, value, halite)

            # remove the hotspots previosly assigned, but not reached
            hotspots[:] = [x for x in hotspots if x[0] not in game.loiter_assignments]

            targets = sorted(hotspots, key=lambda item: item[1])

            if DEBUG & (DEBUG_GAME): logging.info("Game - Found {} targets".format(len(targets)))

            threshold -= TARGET_THRESHOLD_STEP

            if threshold < TARGET_THRESHOLD_MIN:
                if DEBUG & (DEBUG_GAME): logging.info("Game - Target threshold {} reached min threshold {}. Aborting target generation".format(threshold, TARGET_THRESHOLD_MIN))
                break

            #
            # end target generation
            #

        if DEBUG & (DEBUG_GAME): logging.info("Game - There are {} untasked ships and {} targets available.".format(untasked_ships_cnt, len(targets)))

        logging.debug("Targets: {}".format(targets))

        logging.debug("Loiter assignments: {}".format(game.loiter_assignments))

    else:
        targets = []

    if DEBUG & (DEBUG_TIMING): logging.info("Time - Turn setup elapsed time: {}".format(round(time.time() - turn_start_time, 2)))

    #
    # initialize the ship states
    #

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
                "path": [],
                "assignment_distance": 0,
                "assignment_duration": 0,
                "explore_start": 0
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
        ship.explore_start = ship_states[ship.id]["explore_start"]
        ship.assignment_distance = ship_states[ship.id]["assignment_distance"]
        ship.assignment_duration = ship_states[ship.id]["assignment_duration"]

        # note, some ship state attribs are not stored on the actual ship object:
        # e.g. prior_position, prior_halite_amount

    #
    # handle each ship for this turn
    #
    for ship in my_ships:
        dropoff_position = get_dropoff_positions(game, ship)

        if DEBUG & (DEBUG_GAME) and ship.christening != game.turn_number:
            suffix = "to {} and is {} away".format(ship.path[0], round(game_map.calculate_distance(ship.position, ship.path[0], "manhatten"))) if ship.path and ship.status == "transiting" else ""
            logging.info("Game - Ship {} at {} has {} halite and is {} {}".format(ship.id, ship.position, ship.halite_amount, ship.status, suffix))

        #
        # status - returning
        #
        if ship.status == "returning" or ship.position == dropoff_position:
            # Returning - arrived
            if ship.position == dropoff_position:

                # if status != "returning" accidentail dropoff
                # if ship_states[ship.id]["prior_position"] and ship_states[ship.id]["prior_position"] != dropoff_position:
                #    ship delayed

                # log some data about the previous assignment
                if game.turn_number != ship.christening and ship_states[ship.id]["prior_position"] != dropoff_position:
                    dropoff_amount = ship_states[ship.id]["prior_halite_amount"]
                    game_metrics["trip_data"].append((game.turn_number, ship.id, game.turn_number - ship.last_dock, dropoff_amount, ship.assignment_distance, ship.assignment_duration))
                    if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} completed dropoff of {} halite at {}. Return + explore took {} turns".format(ship.id, dropoff_amount, dropoff_position, game.turn_number - ship.last_dock))

                ship.path.clear() # may not have completed the previous path
                game.update_loiter_assignment(ship) # clear this ships assignment
                ship.assignment_duration = 0
                ship.assignment_distance = 0

                #
                # task/loiter point assignment
                #

                if EXPEDITED_DEPARTURE and game.turn_number <= 6:
                    # takes 6 turns to get the first 4 ships out
                    cardinals = ["w", "n", "s", "e"]
                    hint = cardinals[me.ship_count % 4]
                    loiter_point = get_loiter_point(game, ship, hint)
                    departure_point = ship.position.directional_offset(DIRECTIONS[hint])
                else:
                    hint = None
                    if len(targets) != 0:
                        loiter_point = targets.pop()[0]
                        game.update_loiter_assignment(ship, loiter_point)
                        if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} assigned loiter point {} off target list. {} targets remain".format(ship.id, loiter_point, len(targets)))
                    else:
                        loiter_point = get_loiter_point(game, ship, hint)
                        if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} No targets remain, using random loiter point {}".format(ship.id, loiter_point))
                    departure_point = get_departure_point(game, dropoff_position, loiter_point)

                # calc the path for the assignment
                bases = [me.shipyard.position]
                ship.path, cost = game_map.navigate(departure_point, loiter_point, "astar", {"move_cost": "turns", "excludes":bases}) # heading out to loiter point
                if ship.path is None: # note: path will be [] if loiter_point is closer that departure pt
                    logging.error("Ship {} Error, navigate failed for loiter point {}, path:{}".format(ship.id, loiter_point, ship.path))
                    ship.path = [] # path will be None if failed,
                    ship.path.append(loiter_point) # maybe calc will succeed next time?

                #if departure_point != loiter_point:
                ship.path.append(departure_point) # if loiter_point is closer that departure point, they'll be the same.

                # log some data about the current assignment
                if DEBUG & (DEBUG_NAV_METRICS): game.game_metrics["loiter_distances"].append((game.turn_number, game_map.calculate_distance(ship.position, loiter_point, "manhatten")))
                if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} is heading out with a departure point of {} and loiter point {}. Hint: {}".format(ship.id, departure_point, loiter_point, hint))

                ship.last_dock = game.turn_number
                ship.status = "transiting"
                ship.explore_start = 0
                if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} is now {}".format(ship.id, ship.status))
            else:
                # status returning, not home yet
                if DEBUG & (DEBUG_NAV): logging.info("Ship - Ship {} is {} away from dropoff {}.".format(ship.id, game_map.calculate_distance(ship.position, dropoff_position), dropoff_position))

        #
        # status exploring|transiting --> returning
        #
        elif ship.halite_amount >= constants.MAX_HALITE or ship.is_full:
            if ship.status != "returning":
                if ship.status == "transiting":
                    game_metrics["trip_transit_duration"].append((game.turn_number, ship.id, max(ship.explore_start, game.turn_number) - ship.last_dock, round(game_map.calculate_distance(ship.position, dropoff_position), 2)))
                elif ship.status == "exploring":
                    game_metrics["trip_explore_duration"].append((game.turn_number, ship.id, game.turn_number - ship.explore_start, round(game_map.calculate_distance(ship.position, dropoff_position), 2)))
                else:
                    logging.warn("Unknown status at 'ship full': {}".format(ship.status))

                ship.status = "returning"
                if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} is now {}".format(ship.id, ship.status))

            # chk if ship has an assignment, if so clear it, we're heading home (need to chk position in case became full on assigned pt?)
            current_assignment = game.get_loiter_assignment(ship)
            if current_assignment:
                game.update_loiter_assignment(current_assignment[0])
                if DEBUG & (DEBUG_GAME): logging.info("Ship - Ship {} at {} is full and didn't reach loiter assignment {}, popped assignment".format(ship.id, ship.position, current_assignment[0]))

            ship.path, cost = game_map.navigate(ship.position, dropoff_position, "dock") # returning to shipyard/dropoff

            if not ship.path:
                ship.path = [] # path might be None if failed
                logging.error("Ship {} Error, navigate failed for dropoff {}".format(ship.id, dropoff_position))

        #
        # status exploring|transiting (exploring when ship.path != 0)
        #
        else:
            ship.assignment_duration += 1

            if ship.path:
                if ship.status != "transiting":
                    ship.status = "transiting"
                    if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} is now {}".format(ship.id, ship.status))
            else:
                if ship.status != "exploring":
                    ship.status = "exploring"
                    if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} is now {}".format(ship.id, ship.status))
                    ship.explore_start = game.turn_number
                    game_metrics["trip_transit_duration"].append((game.turn_number, ship.id, game.turn_number - ship.last_dock, round(game_map.calculate_distance(ship.position, dropoff_position), 2)))

            if game.get_loiter_assignment(ship.position):
                game.update_loiter_assignment(ship.position)
                if DEBUG & (DEBUG_GAME): logging.info("Ship - Ship {} reached loiter assignment {}, popped assignment".format(ship.id, ship.position))

        #
        # Move
        #

        # if cell is below mining threshold then continue,
        # if the ship is above cargo threshold continue
        # else we'll stay in place and mine
        if move_ok(game, ship):
            #
            # exploring (not mining)
            #
            if ship.path and ship.position == ship.path[-1]:
                # if we're already at our next position, pop it, don't waste a turn - why is this happening?
                logging.warning("Ship {} popped a useless point {}".format(ship.id, ship.path[-1]))
                ship.path.pop()

            if ship.status == "exploring":
                move = get_move(game, ship, "density")
                if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} is exploring to the {}".format(ship.id, move))
            elif ship.status == "transiting":
                args = {
                    "waypoint_algorithm": "astar",
                    "move_cost": "turns"
                }
                move = get_move(game, ship, "nav", args) # path scheme = algo for incomplete path
                if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} is {} {}".format(ship.id, ship.status, move))
            elif ship.status == "returning":
                move = get_move(game, ship, "nav", "naive") # returning will break if a waypoint resolution other than naive is used
                if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} is {} {}".format(ship.id, ship.status, move))
            else:
                move = get_move(game, ship, "density", "density")
                logging.error("Error - Ship {} should move, but has an unexpected status {}, falling back to density move {}".format(ship.id, ship.status, move))

            if move:
                ship.assignment_distance += 1
                game.command_queue[ship.id] = ship.move(move)
        else:
            #
            # mining
            #
            if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} is mining".format(ship.id))
            game.command_queue[ship.id] = ship.stay_still()

        ship.assignment_duration += 1

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
        ship_states[ship.id]["explore_start"] = ship.explore_start
        ship_states[ship.id]["assignment_distance"] = ship.assignment_distance
        ship_states[ship.id]["assignment_duration"] = ship.assignment_duration

        #
        # end for each ship
        #

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

    if DEBUG & (DEBUG_SHIP_STATES): logging.info("Game - end ship_states: {}".format(ship_states))

    if DEBUG & (DEBUG_GAME_METRICS):
        mined_this_turn = sum(map(lambda i: i[2] if i[0] == game.turn_number else 0, game_metrics["mined"]))
        logging.info("Game - Mined this turn: {}".format(mined_this_turn))
        logging.info("Game - Turn mining rate: {}".format(0 if not len(my_ships) else mined_this_turn / len(my_ships)))
        logging.info("Game - Mining rate: {}".format(round(game.get_mining_rate(MINING_RATE_LOOKBACK), 2)))

        logging.info("Game - Total mined: {}".format(sum(x[2] for x in game_metrics["mined"])))
        logging.info("Game - Total gathered: {}".format(sum(x[2] for x in game_metrics["gathered"])))
        logging.info("Game - Total burned: {}".format(sum(x[2] for x in game_metrics["burned"])))

        # profit = gathered - spent
        logging.info("Game - Profit: {} {}".format(turn_profit, cumulative_profit))

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

        logging.info("Game - Ship mining rate averages (Last {} turns):".format(min(game.turn_number, MINING_RATE_LOOKBACK)))
        for s_id in avg_mined_by_ship:
            logging.info("Game - {:4d}: {}".format(s_id, round(avg_mined_by_ship[s_id], 2)))

        logging.info("Game - Ship yields (Last {} turns):".format(min(game.turn_number, MINING_RATE_LOOKBACK)))
        for s_id, halite in mined_by_ship.items():
            logging.info("Game - {:4d}: {}".format(s_id, halite))

    if DEBUG & (DEBUG_TIMING):
        logging.info("Time - Min turn time: {}".format(min(game_metrics["turn_time"], key = lambda t: t[1])))
        logging.info("Time - Max turn time: {}".format(max(game_metrics["turn_time"], key = lambda t: t[1])))
        logging.info("Time - Avg turn time: {:.4f}".format(np.mean(game_metrics["turn_time"], axis=0)[1]))
        logging.info("Time - Turn time: {}".format(round(time.time() - turn_start_time, 4)))

    #
    # last turn output
    #
    if game.turn_number == constants.MAX_TURNS:
        if DEBUG & (DEBUG_NAV_METRICS):
            logging.info("Nav - Loiter multiples: {}".format(game_metrics["loiter_multiples"]))
            logging.info("Nav - Loiter offsets: {}".format(game_metrics["loiter_offsets"]))
            logging.info("Nav - Loiter distances: {}".format(game_metrics["loiter_distances"]))
            logging.info("Nav - Raw loiter points: {}".format(game_metrics["raw_loiter_points"]))

        if DEBUG & (DEBUG_GAME_METRICS):

            # trip_data 0:turn (end of trip) 1:ship 2:duration 3:halite 4:assigned loiter distance
            logging.info("Game - Total trips completed: {}".format(len(game_metrics["trip_data"])))

            avg_trip_duration = round(np.mean(game_metrics["trip_data"], axis=0)[2], 2)
            logging.info("Game - Avg. trip duration: {}".format(avg_trip_duration))

            avg_halite_gathered = round(np.mean(game_metrics["trip_data"], axis=0)[3], 2)
            logging.info("Game - Avg. halite gathered: {}".format(avg_halite_gathered))

            # trip_explore_duration 0:turn (end of explore) 1:ship 2:duration 3:distance from dropoff
            trip_explore_duration = round(np.mean(game_metrics["trip_explore_duration"], axis=0)[3], 2)
            logging.info("Game - Avg. explore duration: {}".format(trip_explore_duration))

            # trip_transit_duration 0:turn (end of return) 1:ship 2:duration 3:distance from dropoff
            trip_transit_duration = round(np.mean(game_metrics["trip_transit_duration"], axis=0)[2], 2)
            logging.info("Game - Avg. transit duration: {}".format(trip_transit_duration))

            avg_return_duration = avg_trip_duration - trip_explore_duration - trip_transit_duration
            logging.info("Game - Avg. return duration: {}".format(round(avg_return_duration, 2)))

        if DEBUG & (DEBUG_TIMING):
            logging.info("Time - Min. turn time: {}".format(min(game_metrics["turn_time"], key = lambda t: t[1])))
            logging.info("Time - Max. turn time: {}".format(max(game_metrics["turn_time"], key = lambda t: t[1])))
            logging.info("Time - Avg. turn time: {:.4f}".format(np.mean(game_metrics["turn_time"], axis=0)[1]))
            logging.info("Time - Elapsed time: {}".format(round(time.time() - game_start_time, 2)))

        if DEBUG & (DEBUG_OUTPUT_GAME_METRICS):
            dump_stats(game, game_metrics, "all")

    #
    # resolve collisions
    #
    resolve_collsions(game)

    if (DEBUG & (DEBUG_COMMANDS)): logging.info("Game - command queue: {}".format(game.command_queue))

    # check if we can spawn a ship. Make sure to check after all moves have been finalized
    if spawn_ok(game):
        game.command_queue[-1] = me.shipyard.spawn()
        if DEBUG & (DEBUG_GAME): logging.info("Game - Ship spawn request")

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(list(game.command_queue.values()))


