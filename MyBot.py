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
botName = "MyBot.v26"
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
    game.command_queue.clear()
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

        while len(targets) < len(my_ships):
            hottest_areas = np.ma.MaskedArray(cell_value_map, mask = [cell_value_map <= threshold], fill_value = 0, copy=False)

            if DEBUG & (DEBUG_TASKS):
                if threshold == TARGET_THRESHOLD_DEFAULT:
                    logging.info("Task - Generating targets, threshold: {}".format(threshold))
                else:
                    logging.info("Task - Ships({}) exceeds the {} available targets. Generating targets using threshold {}".format(len(my_ships), len(targets), threshold))

            if DEBUG & (DEBUG_CV_MAP) and threshold != TARGET_THRESHOLD_DEFAULT:
                np.ma.masked_print_option.set_display("---")
                np.set_printoptions(precision=1, linewidth=240, suppress=True, threshold=np.inf)
                logging.info("cell_values:\n{}".format(cell_value_map.astype(np.int)))
                logging.debug("hottest_areas:\n{}".format(hottest_areas.astype(np.int)))
                np.set_printoptions(precision=1, linewidth=240, suppress=True, threshold=64)

            y_vals, x_vals = hottest_areas.nonzero()

            hotspots = []
            for x, y in zip(x_vals, y_vals):
                p = Position(x, y)
                hotspots.append((p, round(cell_value_map[y][x]), game_map[p].halite_amount)) # (position, value, halite)

            # remove the hotspots previosly assigned, but not reached
            hotspots[:] = [x for x in hotspots if x[0] not in game.loiter_assignments]

            targets = sorted(hotspots, key=lambda item: item[1])

            if DEBUG & (DEBUG_TASKS): logging.info("Task - Found {} targets".format(len(targets)))

            if len(targets) < len(my_ships):
                threshold -= TARGET_THRESHOLD_STEP

            if threshold < TARGET_THRESHOLD_MIN:
                if DEBUG & (DEBUG_TASKS): logging.info("Task - Target threshold {} reached min threshold {}. Aborting target generation".format(threshold, TARGET_THRESHOLD_MIN))
                break

            #
            # end target generation
            #

        if DEBUG & (DEBUG_TASKS): logging.info("Task - There are {} ships and {} targets available.".format(len(my_ships), len(targets)))

        if DEBUG & (DEBUG_TASKS): logging.info("Task - Targets: {}".format(list_to_short_string(targets, 2)))

        if DEBUG & (DEBUG_TASKS): logging.info("Task - Loiter assignments: {}".format(game.loiter_assignments))

    else:
        targets = []

    if DEBUG & (DEBUG_TIMING): logging.info("Time - Turn setup elapsed time: {}".format(round(time.time() - turn_start_time, 2)))

    #
    # initialize the ship states
    #

    # sort the ships by halite, this helps give returning ships priority/helps with
    # traffic issues around bases until better collision mgmt is in place
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
            if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} is a new ship. t{}".format(ship.id, game.turn_number))
            me.ship_count += 1

            turn_spent = constants.SHIP_COST
            game_metrics["spent"].append((game.turn_number, turn_spent))

            ship_states[ship.id] = {
                "last_seen": game.turn_number,
                "prior_position": None,
                "prior_halite_amount": 0,
                "status": "returning",
                "last_dock": game.turn_number,
                "christening": game.turn_number,
                "path": [],
                "assignment_distance": 0,
                "assignment_duration": 0,
                "explore_start": 0,
                "blocked_by": None,
                "mining_threshold": SHIP_MINING_THRESHOLD_DEFAULT,
                "assignments": [],
                "position": ship.position
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
        ship.blocked_by = ship_states[ship.id]["blocked_by"]
        ship.mining_threshold = ship_states[ship.id]["mining_threshold"]
        ship.assignments = ship_states[ship.id]["assignments"]

        if ship.position != ship_states[ship.id]["position"]:
            logging.warn("Ship {} has an inconsistent position. State: {}, Server: {}".format(ship.id, ship_states[ship.id]["position"], ship.position))

        # note, some ship state attribs are not stored on the actual ship object:
        # e.g. prior_position, prior_halite_amount

    #
    # remove base clear request that are no longer valid
    #
    for bcr in game.base_clear_request[:]:
        cell = game_map[bcr["position"]]
        if not cell.is_occupied or cell.ship.id != bcr["ship"].id:
            game.base_clear_request.remove(bcr)

    #
    # chk for sos events
    #
    for sos in game.sos_calls[:]:
        respond_to_sos(game, sos)
        game.sos_calls.remove(sos)

    #
    # chk for end game
    #
    homing_count = 0
    remaining_turns = constants.MAX_TURNS - game.turn_number
    if remaining_turns <= game_map.width:
        for s in my_ships:
            if s.status != "homing" and game_map.calculate_distance(s.position, get_base_positions(game, s.position)) * HOMING_OVERHEAD >= remaining_turns:
                if not game.end_game:
                    game.end_game = game.turn_number

                s.path.clear()
                s.status = "homing"

                base_position = get_base_positions(game, s.position)
                arrival_direction = game_map.get_relative_direction(base_position, s.position)
                arrival_offset = DIRECTIONS[arrival_direction]
                arrival_point = base_position + Position(arrival_offset[0], arrival_offset[1])

                s.path, cost = game_map.navigate(s.position, arrival_point, "astar", {"move_cost": "turns"})
                s.path.insert(0, base_position)

                homing_count += 1

                if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} is now homing from the {}. t{}".format(s.id, arrival_direction, game.turn_number))

                if homing_count >= 4:
                    break

    #
    # handle each ship for this turn
    #
    for ship in my_ships:
        base_position = get_base_positions(game, ship.position)

        if DEBUG & (DEBUG_GAME) and ship.christening != game.turn_number:
            suffix = "to {} and is {} away".format(ship.path[0], round(game_map.calculate_distance(ship.position, ship.path[0], "manhatten"))) if ship.path and ship.status == "transiting" else ""
            logging.info("Game - Ship {} at {} has {} halite and is {} {}".format(ship.id, ship.position, ship.halite_amount, ship.status, suffix))

        #
        # status - returning
        #
        if game.end_game:
            if ship.position == base_position:
                game.command_queue[ship.id] = ship.move("o")

        elif ship.status == "returning" or ship.position == base_position:
            # Returning - arrived
            if ship.position == base_position:

                ship.mining_threshold = SHIP_MINING_THRESHOLD_DEFAULT

                # chk if there is a clear request
                if game.base_clear_request:
                    clear_request = game.base_clear_request.pop()
                    cell = game_map[clear_request["position"]]

                    if cell.is_occupied and cell.ship.owner != me.id:
                        move_offset = clear_request["position"] - base_position
                        move = Direction.convert((move_offset.x, move_offset.y))

                        if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} responded to base clear request for {}. Moving {}".format(ship.id, clear_request["position"], move))

                        game.command_queue[ship.id] = ship.move(move)
                        game_map[ship].mark_safe()
                        game_map[clear_request["position"]].mark_unsafe(ship)

                        continue
                    else:
                        if DEBUG & (DEBUG_NAV): logging.info("Nav - Clear request canceled for {}. Cell is clear".format(clear_request["position"]))

                # log some data about the previous assignment
                if game.turn_number != ship.christening and ship_states[ship.id]["prior_position"] != base_position:
                    drop_amount = ship_states[ship.id]["prior_halite_amount"]
                    game_metrics["trip_data"].append((game.turn_number, ship.id, game.turn_number - ship.last_dock, drop_amount, ship.assignment_distance, ship.assignment_duration))
                    if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} completed drop of {} halite at {}. Return + explore took {} turns. t{}".format(ship.id, drop_amount, base_position, game.turn_number - ship.last_dock, game.turn_number))

                # debug
                if ship.path:
                    if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} at base with a residual path of {}".format(ship.id, list_to_short_string(ship.path, 2)))
                    ship.path.clear()

                # chk for previous assignment
                assignment = game.get_loiter_assignment(ship) # assignment -> (position, ship Id)
                if assignment:
                    if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} failed to complete assignment {}".format(ship.id, assignment[0]))
                    game.update_loiter_assignment(assignment[0])

                ship.assignment_duration = 0
                ship.assignment_distance = 0

                #
                # task/loiter point assignment
                #

                if len(targets) != 0:
                    assignment_target = targets.pop()
                    loiter_point = assignment_target[0]

                    if assignment_target[2] < (ship.mining_threshold * 1.25):
                        if DEBUG & (DEBUG_TASKS): logging.debug("Task - Ship {} has a mining threshold of {}, but assigment {} has {} halite. t{}".format(ship.id, ship.mining_threshold, loiter_point, assignment_target[2], game.turn_number))
                        ship.mining_threshold = 25

                    game.update_loiter_assignment(ship, loiter_point)
                    if DEBUG & (DEBUG_TASKS): logging.info("Task - Ship {} assigned loiter point {} off target list. {} targets remain, t{}".format(ship.id, loiter_point, len(targets), game.turn_number))
                else:
                    loiter_point = get_loiter_point(game, ship)
                    if DEBUG & (DEBUG_TASKS): logging.info("Task - Ship {} No targets remain, using random loiter point {}".format(ship.id, loiter_point))

                departure_point = get_departure_point(game, base_position, loiter_point)

                # calc the path for the assignment
                bases = [me.shipyard.position]
                ship.path, cost = game_map.navigate(departure_point, loiter_point, "astar", {"move_cost": "turns", "excludes":bases}) # heading out to loiter point
                if ship.path is None: # note: path will be [] if loiter_point is closer than the departure point
                    logging.error("Ship {} Error, navigate failed for loiter point {}, path:{}".format(ship.id, loiter_point, ship.path))
                    ship.path = [] # path will be None if failed,
                    ship.path.append(loiter_point) # maybe calc will succeed next time?

                #if departure_point != loiter_point:
                ship.path.append(departure_point) # if loiter_point is closer that departure point, they'll be the same.

                # log some data about the current assignment
                if DEBUG & (DEBUG_NAV_METRICS): game.game_metrics["loiter_distances"].append((game.turn_number, game_map.calculate_distance(ship.position, loiter_point, "manhatten")))
                if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} is heading out with a departure point of {} and loiter point {}.".format(ship.id, departure_point, loiter_point))

                ship.last_dock = game.turn_number
                ship.status = "transiting"
                ship.explore_start = 0
                if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} is now {}. t{}".format(ship.id, ship.status, game.turn_number))
            else:
                # status returning, not home yet
                if DEBUG & (DEBUG_NAV): logging.info("Ship - Ship {} is {} away from base {}.".format(ship.id, game_map.calculate_distance(ship.position, base_position), base_position))

        #
        # status exploring|transiting --> returning
        #
        elif ship.halite_amount >= constants.MAX_HALITE or ship.is_full:
            if ship.status != "returning":
                if ship.status == "transiting":
                    game_metrics["trip_transit_duration"].append((game.turn_number, ship.id, max(ship.explore_start, game.turn_number) - ship.last_dock, round(game_map.calculate_distance(ship.position, base_position), 2)))
                elif ship.status == "exploring":
                    game_metrics["trip_explore_duration"].append((game.turn_number, ship.id, game.turn_number - ship.explore_start, round(game_map.calculate_distance(ship.position, base_position), 2)))
                else:
                    logging.warn("Unknown status at 'ship full': {}".format(ship.status))

                ship.status = "returning"
                if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} is now {}. t{}".format(ship.id, ship.status, game.turn_number))

            # chk if ship has an assignment, if so clear it, we're heading home (need to chk position in case became full on assigned pt?)
            if ship.assignments and ship.assignments[-1] != ship.position:
                if DEBUG & (DEBUG_GAME): logging.info("Ship - Ship {} at {} is full and did not reach loiter assignment {}. Cleared assignment. t{}".format(ship.id, ship.position, ship.assignments[-1], game.turn_number))
                game.update_loiter_assignment(ship)

            ship.path, cost = game_map.navigate(ship.position, base_position, "dock") # returning to base

            if not ship.path:
                ship.path = [] # path might be None if failed
                logging.error("Ship {} Error, navigate failed for base {}".format(ship.id, base_position))

        #
        # status exploring|transiting (exploring when ship.path != 0)
        #
        else:
            ship.assignment_duration += 1

            if ship.status == "transiting":

                if ship.assignments: #  and ship.assignments[-1] == ship.position:
                    assignment_distance = game_map.calculate_distance(ship.assignments[-1], ship.position)
                    assignment_cell = game_map[ship.assignments[-1]]
                    if assignment_distance == 0:
                        if DEBUG & (DEBUG_GAME): logging.info("Ship - Ship {} reached loiter assignment {} t{}".format(ship.id, ship.assignments[-1], game.turn_number))
                    elif assignment_distance == 1 and assignment_cell.is_occupied and assignment_cell.ship.owner == me.id and assignment_cell.position != base_position:
                        if DEBUG & (DEBUG_GAME): logging.info("Ship - Ship {} approached loiter assignment {} It is friendly occupied by ship {}. Clearing assignment. t{}".format(ship.id, ship.assignments[-1], assignment_cell.ship.id, game.turn_number))
                        game.update_loiter_assignment(ship)
                        if not ship.path:
                            logging.error("Ship {} has an assignment, {}, with no path. t{}".format(ship.id, assignment_cell.position, game.turn_number))
                        while ship.path[-1] != assignment_cell.position:
                            ship.path.pop()
                        ship.path.pop()

            if ship.path:
                if ship.status != "transiting":
                    ship.status = "transiting"
                    if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} is now {}. t{}".format(ship.id, ship.status, game.turn_number))
            else:
                if ship.status != "exploring":
                    ship.status = "exploring"
                    if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} is now {}. t{}".format(ship.id, ship.status, game.turn_number))
                    ship.explore_start = game.turn_number
                    game_metrics["trip_transit_duration"].append((game.turn_number, ship.id, game.turn_number - ship.last_dock, round(game_map.calculate_distance(ship.position, base_position), 2)))

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
            elif ship.status == "transiting":
                move = get_move(game, ship, "nav", {"waypoint_algorithm": "astar", "move_cost": "turns"}) # path scheme = algo for incomplete path
            elif ship.status == "returning":
                move = get_move(game, ship, "nav", "naive") # returning will break if a waypoint resolution other than naive is used. Why?
            elif ship.status == "homing":
                move = get_move(game, ship, "nav", {"waypoint_algorithm": "astar", "move_cost": "turns"}) # path scheme = algo for incomplete path
            else:
                raise RuntimeError("Ship {} has an invalid status: {}".format(ship.id, ship.status))

            if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} is {} to the {}".format(ship.id, ship.status, move))

            if move:
                ship.assignment_distance += 1
                game.command_queue[ship.id] = ship.move(move)
                if ship.assignments and ship.assignments[-1] == ship.position and move != "o":
                    if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} completed assignment {}, clearing assignment. t{}".format(ship.id, ship.assignments[-1], game.turn_number))
                    game.update_loiter_assignment(ship)

        else:
            #
            # mining
            #
            if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} is mining".format(ship.id))
            move = "o"
            game.command_queue[ship.id] = ship.move(move)

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
        ship_states[ship.id]["blocked_by"] = ship.blocked_by
        ship_states[ship.id]["mining_threshold"] = ship.mining_threshold
        ship_states[ship.id]["assignments"] = ship.assignments
        ship_states[ship.id]["position"] = None if move is None else get_position_from_move(game, ship, move)

        #
        # end for each ship
        #

    #
    # collect game metrics
    #
    turn_profit = turn_gathered - turn_spent
    cumulative_profit += (turn_gathered - turn_spent)
    game_metrics["profit"].append((game.turn_number, turn_profit))
    game_metrics["turn_time"].append((game.turn_number, round(time.time() - turn_start_time, 4)))
    game_metrics["mining_rate"].append((game.turn_number, round(game.get_mining_rate(MINING_RATE_LOOKBACK), 2)))
    game_metrics["ship_count"].append((game.turn_number, len(my_ships)))

    #
    # check of lost ships
    #
    lost_ships = []
    if not game.end_game:
        for s_id in ship_states:
            if not me.has_ship(s_id):
                lost_ships.append(s_id)

        for s_id in lost_ships:
            sos_evt = {
                "s_id": s_id,
                "halite": ship_states[s_id]["prior_halite_amount"],
                "position": ship_states[s_id]["position"]
            }
            game.sos_calls.append(sos_evt)
            if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} lost. Last seen at {} on turn {} with {} halite. t{}".format(s_id, ship_states[s_id]["prior_position"], ship_states[s_id]["last_seen"], ship_states[s_id]["prior_halite_amount"], game.turn_number))
            ship_states.pop(s_id, None)

    #
    # debug info for each turn
    #

    if DEBUG & (DEBUG_SHIP_STATES): logging.info("Game - end ship_states:\n{}".format(ship_states_to_string(ship_states)))

    if DEBUG & (DEBUG_GAME_METRICS):
        mined_this_turn = sum(map(lambda i: i[2] if i[0] == game.turn_number else 0, game_metrics["mined"]))
        logging.info("Game - Mined this turn: {}".format(mined_this_turn))
        logging.info("Game - Turn mining rate: {}".format(0 if not len(my_ships) else round(mined_this_turn / len(my_ships), 2)))
        logging.info("Game - Mining rate (Last {} turns): {}".format(MINING_RATE_LOOKBACK, round(game.get_mining_rate(MINING_RATE_LOOKBACK), 2)))

        logging.info("Game - Total mined: {}".format(sum(x[2] for x in game_metrics["mined"])))
        logging.info("Game - Total gathered: {}".format(sum(x[2] for x in game_metrics["gathered"])))
        logging.info("Game - Total burned: {}".format(sum(x[2] for x in game_metrics["burned"])))

        # profit = gathered - spent
        logging.info("Game - Profit: turn: {},  cumulative: {}".format(turn_profit, cumulative_profit))

    if DEBUG & (DEBUG_SHIP_METRICS):
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

            # trip_explore_duration 0:turn (end of explore) 1:ship 2:duration 3:distance from base
            trip_explore_duration = round(np.mean(game_metrics["trip_explore_duration"], axis=0)[3], 2)
            logging.info("Game - Avg. explore duration: {}".format(trip_explore_duration))

            # trip_transit_duration 0:turn (end of return) 1:ship 2:duration 3:distance from base
            trip_transit_duration = round(np.mean(game_metrics["trip_transit_duration"], axis=0)[2], 2)
            logging.info("Game - Avg. transit duration: {}".format(trip_transit_duration))

            avg_return_duration = avg_trip_duration - trip_explore_duration - trip_transit_duration
            logging.info("Game - Avg. return duration: {}".format(round(avg_return_duration, 2)))

            mined_by_ship = {}
            for line in game.game_metrics["mined"]:
                s_id = line[1]
                halite = line[2]
                mined_by_ship[s_id] = (mined_by_ship[s_id] + halite) if s_id in mined_by_ship else halite

            logging.info("Game - Ship yields:")
            for s_id, halite in sorted(mined_by_ship.items()):
                logging.info("Game - {:4d}: {}".format(s_id, halite))

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
    resolve_collsions(game, ship_states)

    # check if we can spawn a ship. Make sure to check after all moves have been finalized
    if spawn_ok(game):
        if DEBUG & (DEBUG_GAME): logging.info("Game - Ship spawn request")
        game.command_queue[-1] = me.shipyard.spawn()

    if (DEBUG & (DEBUG_COMMANDS)): logging.info("Game - command queue: {}".format(game.command_queue))

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(list(game.command_queue.values()))


