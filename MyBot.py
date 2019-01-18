#!/usr/bin/env python3
# Python 3.6

import hlt

from hlt import constants

import logging
import datetime
import math
import time
import numpy as np
import cProfile

import copy

from operator import attrgetter, itemgetter
from scipy import ndimage

from myutils.utils import *
from myutils.constants import *

from myutils.mytasks import make_dropoff_task

#
# main
#

""" <<<Game Begin>>> """

# To view profiling ./analyze_stats.py profiler_results.dmp profiling_results.txt
if DEBUG & (DEBUG_PROFILING):
    pr = cProfile.Profile()
    pr.enable()

game_start_time = time.time()
game = hlt.Game()
ship_states = {} # keep ship state inbetween turns
botName = "MyBot.v28"
cumulative_profit = 5000

if DEBUG & (DEBUG_TIMING): logging.info("Time - Initialization elapsed time: {}".format(round(time.time() - game_start_time, 2)))

if DEBUG & (DEBUG_CV_MAP):
    np.ma.masked_print_option.set_display("...")
    np.set_printoptions(precision=1, linewidth=280, suppress=True, threshold=np.inf)
else:
    np.set_printoptions(precision=1, linewidth=280, suppress=True, threshold=64)

# Deployed dropoffs
#
# To deploy a dropoff, add it to the dropoff_deployment_queue. dropoff_deployment_queue
# is a list of tuple(position, min_deployment_turn). Once the dropoff is deployed it is
# added to dropoff_deployments dictionary keyed on position, with a value of deployed turn
# number.
#
# Notes:
#  - To add a dropoff at the current dropoff position use None as the position.
#  - To add a dropoff immediately simply use a turn number of 0
#  - A queued entry without a turn is skipped/remains in the queue
#  - A queued entry is a unnormalized positions is aborted (popped from queue, added
#    to dropoff_deployments with a turn of None.

# non deployed dropoff, key:point, value turn deployed
dropoff_deployment_queue = []

# deployed dropoffs, both successful and aborted
dropoff_deployments = {}


dropoff_deployment_queue.append((None, 150))


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
    target_sets = {}

    # convenience vars
    me = game.me
    game_map = game.game_map
    game_metrics = game.game_metrics

    game.update_frame()

    my_ships = me.get_ships()

    #
    # update stats - ship count need to be updated before cv map gen
    #
    game_metrics["ship_count"].append((game.turn_number, len(my_ships)))

    if False:
        turn_spent += constants.DROPOFF_COST

    #
    # Generate hotspots, loiter assignments and areas
    #
    if USE_CELL_VALUE_MAP:
        player_count = len(game.players)

        if player_count == 2 and game.game_map.width in [56, 64]:
            mining_rate_mult = CV_MINING_RATE_MULTIPLIER_OPEN
        elif player_count == 4 and game.game_map.width in [32, 40]:
            mining_rate_mult = CV_MINING_RATE_MULTIPLIER_CONGESTED
        else:
            mining_rate_mult = CV_MINING_RATE_MULTIPLIER_DEFAULT

        #
        # build target sets
        #

        cv_map_start_time = time.time()

        for base_position in get_base_positions(game):
            target_sets[base_position] = []

            # first call to a cv_map position triggers a cache load
            cell_value_map = game_map.get_cell_value_map(base_position, mining_rate_mult * game.get_mining_rate())

            if cell_value_map is None:
                raise RuntimeError("cv map is None")

            if DEBUG & (DEBUG_CV_MAP):
                if game.turn_number in [1, 2, 25, 50] + list(range(0, constants.MAX_TURNS + 100, 100)):
                    logging.info("cell_values({}):\n{}".format(base_position, cell_value_map.astype(np.int)))

            if DEBUG & (DEBUG_OUTPUT_GAME_METRICS):
                if game.turn_number in [1, 50] + list(range(0, constants.MAX_TURNS + 100, 100)):
                    dump_data_file(game, cell_value_map, "cv_map_turn_" + str(game.turn_number))

        if DEBUG & (DEBUG_TIMING): logging.info("Time - Cell Value Map generation elapsed time: {}".format(round(time.time() - cv_map_start_time, 2)))

        target_list_start_time = time.time()

        #
        # for each base, generate a set of minging targets
        #

        hottest_areas = {}

        for target_key in target_sets.keys():
            threshold = TARGET_THRESHOLD_DEFAULT

            # debug
            tmp_time = time.time()

            cv_map = game_map.get_cell_value_map(target_key, mining_rate_mult * game.get_mining_rate())

            # debug
            logging.debug("tmp_time: {}".format(round(time.time() - tmp_time)))

            while len(target_sets[target_key]) < len(my_ships):
                hottest_areas[target_key] = np.ma.MaskedArray(cv_map, mask = [cv_map <= threshold], fill_value = 0, copy=False)

                if DEBUG & (DEBUG_GAME):
                    if threshold == TARGET_THRESHOLD_DEFAULT:
                        logging.info("Game - Generating targets, threshold: {}".format(threshold))
                    else:
                        logging.info("Game - Ships({}) exceeds the {} available targets. Generating targets using threshold {}".format(len(my_ships), len(target_sets[target_key]), threshold))

                if DEBUG & (DEBUG_CV_MAP):
                    if game.turn_number in [1, 2, 25, 50] + list(range(0, constants.MAX_TURNS + 100, 100)):
                        logging.info("hottest_areas({}):\n{}".format(target_key, hottest_areas[target_key].astype(np.int)))

                y_vals, x_vals = hottest_areas[target_key].nonzero()

                hotspots = []
                for x, y in zip(x_vals, y_vals):
                    p = Position(x, y)
                    hotspots.append((p, round(cv_map[y][x]), game_map[p].halite_amount)) # (position, value, halite)

                # remove the hotspots previosly assigned, but not reached
                hotspots[:] = [x for x in hotspots if x[0] not in game.loiter_assignments]

                target_sets[target_key] = sorted(hotspots, key=lambda item: item[1])

                target_count = len(target_sets[target_key])

                if DEBUG & (DEBUG_TASKS): logging.info("Task - Found {} targets for target set {}".format(target_count, target_key))

                if target_count < len(my_ships):
                    threshold -= TARGET_THRESHOLD_STEP

                if threshold < TARGET_THRESHOLD_MIN:
                    if DEBUG & (DEBUG_TASKS): logging.info("Task - Target threshold {} reached min threshold {}. Aborting target generation for target set {}".format(threshold, TARGET_THRESHOLD_MIN, target_key))
                    break

            # end hotspot

            if DEBUG & (DEBUG_TASKS): logging.info("Task - There are {} ships and {} targets available for target set {}.".format(len(my_ships), len(target_sets[target_key]), target_key))
            if DEBUG & (DEBUG_TASKS): logging.info("Task - Targets({}): {}".format(target_key, list_to_short_string(target_sets[target_key], 2)))
            if DEBUG & (DEBUG_TIMING): logging.info("Time - Target list generation elapsed time: {}".format(round(time.time() - target_list_start_time, 2)))


        #
        # For each hotspot/target see if it is part of a larger area of targets. These areas
        # are used in dropoff placement
        #

        dropoff_area_start_time = time.time()

        # TODO IS THE DEEP COPY NECESSARY ???????????????????????????????????????????????????????????????
        #area_map = cv_map # cv_map is retrieved above
        area_map = copy.deepcopy(game_map.get_halite_map())


        # TODO Tune the mask threshold
        # Notes:
        #  - Using % of max fails since a single large cell obscures the rest of the map
        #

        #area_map_threshold = np.max(area_map) * DROPOFF_MASK_THRESHOLD # % of max fails since a single large cell obscure the rest of the map
        #area_map_threshold = np.median(area_map)

        logging.debug("mean: {}, median: {}, p80: {}".format(np.mean(area_map), np.median(area_map), np.percentile(area_map, 80)))

        #area_map_threshold = round(max(np.mean(area_map), np.median(area_map)))

        area_map_threshold = round(np.percentile(area_map, 80))

        #area_map_threshold = SHIP_MINING_THRESHOLD_DEFAULT


        def fthreshold(p1, p2):
            """
            Test p1

            :param p1 Current position
            :param p2 Previous position
            :return Return True if p1 test passed
            """

            np1 = game_map.normalize(p1)
            np2 = game_map.normalize(p2)

            h1 = area_map[np1.y][np1.x]
            h2 = area_map[np2.y][np2.x]

            # TODO Do we need to tune this?
            # - What should decent threshold be?
            # - Should we exclude valves below mining threshold?
            #
            # Note:
            #   - You must specify only traversal up or down, otherwise you'll endless loop if
            #   the map is fullish, i.e. the is a contiguous region from one side to the other
            #   - If peak points are not sorted it doesn't matter which traversal direction is used
            #
            retval = h1 > h2/5 and h1 >= h2 and h1 > SHIP_MINING_THRESHOLD_DEFAULT
            #retval = h1 > SHIP_MINING_THRESHOLD_DEFAULT # too loose
            retval = h1 <= h2 and h1 > SHIP_MINING_THRESHOLD_DEFAULT

            retval =  h1 <= h2 and h1 > area_map_threshold

            #logging.debug("{}({}) > {}({})/2 = {}".format(p1, h1, p2, h2, retval))

            return retval

        # For each target position, see if it is part of an existing area.
        # Target set will be empty if there are not any ships, e.g. turn 1.
        # Reverse the order because we want the highest value first and the list
        # is already sorted so pop pulls the highest off the end
        #tmp_set = target_sets[target_key][:]

        # 1. Get list of halite peaks
        # 2. For each peak, determine it's contiguous area based on threshold
        # 3. Sort peak areas by total value
        # 4. For best peak areas, get it's weighted center, this is the deployment point

        halite_peak_map = np.ma.MaskedArray(area_map, mask = [area_map <= area_map_threshold], fill_value = 0, copy=False)

        if DEBUG & (DEBUG_CV_MAP):
            logging.info("halite_peak_map:\n{}".format(halite_peak_map.astype(np.int)))

        r_vals, c_vals = halite_peak_map.nonzero()

        peaks = []
        peak_positions = {}
        known_points = set()

        peaks_by_value = []
        for r, c in zip(r_vals, c_vals):
            peaks_by_value.append((halite_peak_map[r][c], Position(c, r)))

        peaks_by_value.sort(key=itemgetter(0), reverse=True)

        # for each peak exposed by the mask, get it's contiguous positions
        for halite, pos in peaks_by_value:
            if pos in known_points:
                continue

            peak_positions[pos] = game_map.get_contiguous_area(pos, fthreshold)

            known_points |= peak_positions[pos]

            total_halite = 0
            for p in peak_positions[pos]:
                npos = game_map.normalize(p)
                # area_map is a raw map (e.g. _cell_value_map or _halite_map) and is access rc (not xy)
                total_halite += area_map[npos.y][npos.x]

            peaks.append((pos, total_halite)) # (position, total_halite)

            if DEBUG & (DEBUG_CV_MAP): logging.info("Peak area {} has {} positions with a total value of {}".format(pos, len(peak_positions[pos]), total_halite))

        peaks.sort(key=lambda i: i[1], reverse=True)

        best_peak = peaks[0]
        best_peak_pos = best_peak[0]
        best_peak_total_halite = best_peak[1]

        # lazy, should be single loop?
        min_row = min(peak_positions[best_peak_pos], key=attrgetter("y")).y
        max_row = max(peak_positions[best_peak_pos], key=attrgetter("y")).y
        min_col = min(peak_positions[best_peak_pos], key=attrgetter("x")).x
        max_col = max(peak_positions[best_peak_pos], key=attrgetter("x")).x

        area_mask = np.empty((max_row - min_row + 1, max_col - min_col + 1), dtype="float32")

        for pos in peak_positions[best_peak_pos]:
            npos = game_map.normalize(pos)
            area_mask[pos.y - min_row][pos.x - min_col] = area_map[npos.y][npos.x]

        weighted_center = ndimage.measurements.center_of_mass(area_mask)

        # weighted center is in rc (not xy)
        c_x = round(weighted_center[1])
        c_y = round(weighted_center[0])

        # TODO tune these params
        if len(peak_positions[best_peak_pos]) >= DROPOFF_MIN_POSITIONS and best_peak_total_halite >= DROPOFF_MIN_TOTAL_VALUE:
            current_dropoff_position = game_map.normalize(Position(min_col + c_x, min_row + c_y))
        else:
            current_dropoff_position = None

        if DEBUG & (DEBUG_CV_MAP): logging.info("Best peak is {} with {} positions and a total value of {}. Center is xy({}, {})".format(best_peak_pos, len(peak_positions[best_peak_pos]), best_peak_total_halite, c_x, c_y))

        if DEBUG & (DEBUG_CV_MAP): logging.info("best area:\n{}".format(area_mask))

        if DEBUG & (DEBUG_CV_MAP): logging.info("Game - Current dropoff is {}".format(current_dropoff_position))

        #if game.turn_number > 10:
        #    exit()

        # end target/area generation

        if DEBUG & (DEBUG_TIMING): logging.info("Time - Dropoff area generation elapsed time: {}".format(round(time.time() - dropoff_area_start_time, 2)))
        if DEBUG & (DEBUG_TASKS): logging.info("Task - Loiter assignments: {}".format(game.loiter_assignments))

    else:
        target_sets = {}

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

            turn_spent += constants.SHIP_COST
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
                "tasks": [],
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
        ship.tasks = ship_states[ship.id]["tasks"]

        if ship_states[ship.id]["position"] and ship.position != ship_states[ship.id]["position"]:
            logging.warn("Ship {} has an inconsistent position. State: {}, Server: {}. t{}".format(ship.id, ship_states[ship.id]["position"], ship.position, game.turn_number))

        # note, some ship state attribs are not stored on the actual ship object:
        # e.g. prior_position, prior_halite_amount

    #
    # update stats - update the mining rate as soon as ships are parsed so updated rate is available
    #
    game_metrics["mining_rate"].append((game.turn_number, round(game.get_mining_rate(), 2)))

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
    # Dropoff tasking
    #
    # position -> (turn_trigger, position)

    for deployment_point, deployment_turn in dropoff_deployment_queue:
        if deployment_turn is None:
            continue

        if game.turn_number < deployment_turn:
            continue

        if deployment_point is None:
            deployment_point = current_dropoff_position

        if game_map.needs_normalization(deployment_point):
            logging.error("Invalid deployment point {}. Aborting deployment.".format(deployment_point))
            dropoff_deployments[deployment_point] = None
            continue

        logging.error("popping dropoff deployment {}. deployment_turn: {}".format(deployment_point, deployment_turn))

        dropoff_deployment_queue.pop()
        deployment_ship = False
        deployment_distance = False
        for ship in my_ships:
             distance = game.game_map.calculate_distance(ship.position, deployment_point)
             if not deployment_ship or distance < deployment_distance:
                deployment_ship = ship
                deployment_distance = distance

        if deployment_ship:
            if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} selected for deploying dropoff {}. t{}".format(deployment_ship.id, deployment_point, game.turn_number))
            deployment_ship.path.clear()
            deployment_ship.tasks.append(make_dropoff_task(deployment_point))
            deployment_ship.status = "tasked"
            dropoff_deployments[deployment_point] = game.turn_number
            break
        else:
            logging.warn("Failed to find a deployment ship for dropoff {}. Wil retry.".format(deployment_point))

    #
    # handle each ship for this turn
    #
    for ship in my_ships:
        base_position = get_base_positions(game, ship.position)

        if DEBUG & (DEBUG_GAME) and ship.christening != game.turn_number:
            suffix = "to {} and is {} away".format(ship.path[0], round(game_map.calculate_distance(ship.position, ship.path[0], "manhatten"))) if ship.path and ship.status == "transiting" else ""
            logging.info("Game - Ship {} at {} has {} halite and is {} {}".format(ship.id, ship.position, ship.halite_amount, ship.status, suffix))

        #
        # status - end game/homing
        #
        # don't check for status directly so we can catch normal returning ships as they
        # arrive at base - no need to send them back out
        if game.end_game and ship.position == base_position or ship.status == "homing":
            ship.status = "homing"

        elif ship.status == "tasked":
            if not ship.tasks:
                raise RuntimeError("Ship {} does not have a task.".format(ship.id))

            task = ship.tasks[-1]
            task_complete = task.turn(game, ship)

            if task_complete:
                if DEBUG & (DEBUG_TASKS): logging.info("Task - Ship {} task {} indicates compete, popping task".format(ship.id, task.id))
                ship.tasks.pop()

        #
        # status - returning
        #
        elif ship.status == "returning" or ship.position == base_position:
            # Returning - arrived
            if ship.position == base_position:

                ship.mining_threshold = SHIP_MINING_THRESHOLD_DEFAULT

                # chk if there is a clear request for this ships base
                if game.base_clear_request and game.game_map.calculate_distance(game.base_clear_request[-1]["position"], base_position) == 1:
                    clear_request = game.base_clear_request.pop()
                    cell = game_map[clear_request["position"]]

                    if cell.is_occupied and cell.ship.owner != me.id:
                        move_offset = clear_request["position"] - base_position

                        # get an assignment for clearing ship, ship will probably crash, but in
                        # case the blocking ships moves ... we'll need to move it somewhere.
                        # asbtract this into get_assignment(direction_hint) for use below as well?
                        if target_sets[base_position]:
                            assignment_target = target_sets[base_position].pop()
                            ship.path = assignment_target[0]
                        else:
                            ship.path = get_loiter_point(game, ship)

                        move = Direction.convert((move_offset.x, move_offset.y))

                        if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} responded to base clear request for {}. Moving {}".format(ship.id, clear_request["position"], move))

                        game.command_queue[ship.id] = ship.move(move)
                        game_map[ship].mark_safe()
                        game_map[clear_request["position"]].mark_unsafe(ship)
                        ship.last_dock = game.turn_number
                        ship.status = "transiting"
                        ship.explore_start = 0

                        continue
                    else:
                        if DEBUG & (DEBUG_NAV): logging.info("Nav  - Clear request canceled for {}. Cell is clear".format(clear_request["position"]))

                # log some data about the previous assignment
                if game.turn_number != ship.christening and ship_states[ship.id]["prior_position"] and ship_states[ship.id]["prior_position"] != base_position:
                    drop_amount = ship_states[ship.id]["prior_halite_amount"]

                    game_metrics["assn_duration"].append((game.turn_number, ship.id, game.turn_number - ship.last_dock))

                    game_metrics["assn_duration2"].append((game.turn_number, ship.id, ship.assignment_duration))

                    game_metrics["assn_point_distance"].append((game.turn_number, ship.id, ship.assignment_distance))

                    game_metrics["assn_drop_amount"].append((game.turn_number, ship.id, game.turn_number - ship.last_dock, drop_amount, ship.assignment_distance, ship.assignment_duration))

                    if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} completed drop of {} halite at {}. Return + explore took {}/{} turns. t{}".format(ship.id, drop_amount, base_position, game.turn_number - ship.last_dock, ship.assignment_duration, game.turn_number))

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

                if base_position in target_sets:
                    if not target_sets[base_position]:
                        continue

                    assignment_target = target_sets[base_position].pop()
                    loiter_point = assignment_target[0]

                    if assignment_target[2] < (ship.mining_threshold * 1.32):
                        if DEBUG & (DEBUG_TASKS): logging.info("Task - Ship {} has a mining threshold of {}, but assigment {} has {} halite. t{}".format(ship.id, ship.mining_threshold, loiter_point, assignment_target[2], game.turn_number))
                        ship.mining_threshold = 25

                    game.update_loiter_assignment(ship, loiter_point)
                    if DEBUG & (DEBUG_TASKS): logging.info("Task - Ship {} assigned loiter point {} off target list. {} targets remain, t{}".format(ship.id, loiter_point, len(target_sets[base_position]), game.turn_number))
                else:
                    loiter_point = get_loiter_point(game, ship)
                    if DEBUG & (DEBUG_TASKS): logging.info("Task - Ship {} No targets remain, using random loiter point {}".format(ship.id, loiter_point))

                departure_point = get_departure_point(game, base_position, loiter_point)

                # calc the path for the assignment from departure point to loiter point. If for some reason
                # ship departs wrong side, never cross back over base/current position
                ship.path, cost = game_map.navigate(departure_point, loiter_point, "astar", {"move_cost": "turns", "excludes": [ship.position]})
                if ship.path is None: # path will be [] if loiter_point is closer than the departure point
                    logging.error("Ship {} Error, navigate failed for loiter point {}, path:{}".format(ship.id, loiter_point, ship.path))
                    ship.path = [] # path will be None if failed,
                    ship.path.append(loiter_point) # maybe calc will succeed next time?

                #if departure_point != loiter_point:
                ship.path.append(departure_point) # if loiter_point is closer that departure point, they'll be the same.

                # log some data about the current assignment
                if DEBUG & (DEBUG_NAV_METRICS): game.game_metrics["loiter_distances"].append((game.turn_number, game_map.calculate_distance(ship.position, loiter_point, "manhatten")))
                if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} is heading out with a departure point of {} and loiter point {}.".format(ship.id, departure_point, loiter_point))

                ship.last_dock = game.turn_number
                ship.status = "transiting"
                ship.explore_start = 0
                if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} is now {}. t{}".format(ship.id, ship.status, game.turn_number))
            else:
                # status returning, not home yet
                if DEBUG & (DEBUG_NAV): logging.info("Ship - Ship {} is {} away from base {}.".format(ship.id, game_map.calculate_distance(ship.position, base_position), base_position))

        #
        # status exploring|transiting --> returning
        #
        elif ship.halite_amount >= constants.MAX_HALITE or ship.is_full:
            if ship.status != "returning" and ship.status != "homing":
                if ship.status == "transiting":
                    game_metrics["assn_transit_duration"].append((game.turn_number, ship.id, max(ship.explore_start, game.turn_number) - ship.last_dock, round(game_map.calculate_distance(ship.position, base_position), 2)))
                elif ship.status == "exploring":
                    game_metrics["assn_explore_duration"].append((game.turn_number, ship.id, game.turn_number - ship.explore_start, round(game_map.calculate_distance(ship.position, base_position), 2)))
                else:
                    logging.warn("Unknown status at 'ship full': {}".format(ship.status))

                ship.status = "returning"
                if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} is now {}. t{}".format(ship.id, ship.status, game.turn_number))

            # chk if ship has an assignment, if so clear it, we're heading home (need to chk position in case became full on assigned pt?)
            if ship.assignments and ship.assignments[-1] != ship.position:
                if DEBUG & (DEBUG_GAME): logging.info("Ship - Ship {} at {} is full and did not reach loiter assignment {}. Cleared assignment. t{}".format(ship.id, ship.position, ship.assignments[-1], game.turn_number))
                game.update_loiter_assignment(ship)

            ship.path, cost = game_map.navigate(ship.position, base_position, "dock") # returning to base

            if not ship.path:
                ship.path = [] # path might be None if failed
                logging.error("Ship {} Error, navigate failed for base {}".format(ship.id, base_position))

        #
        # status exploring|transiting - not returning, not full, exploring when ship.path != 0
        #
        else:
            ship.assignment_duration += 1

            if ship.path:
                if ship.status != "transiting":
                    ship.status = "transiting"
                    if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} is now {}. t{}".format(ship.id, ship.status, game.turn_number))
            else:
                if ship.status != "exploring":
                    ship.status = "exploring"
                    if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} is now {}. t{}".format(ship.id, ship.status, game.turn_number))
                    ship.explore_start = game.turn_number
                    game_metrics["assn_transit_duration"].append((game.turn_number, ship.id, game.turn_number - ship.last_dock, round(game_map.calculate_distance(ship.position, base_position), 2)))

            if ship.status == "transiting":
                if ship.assignments: #  and ship.assignments[-1] == ship.position:
                    assignment_cell = game_map[ship.assignments[-1]]
                    if ship.position == assignment_cell.position:
                        if DEBUG & (DEBUG_GAME): logging.info("Ship - Ship {} reached loiter assignment {} t{}".format(ship.id, ship.assignments[-1], game.turn_number))
                    elif len(ship.path) > 1 and ship.path[-2] == ship.assignments[-1] and assignment_cell.is_occupied and assignment_cell.ship.owner == me.id and assignment_cell.position != base_position:
                        if DEBUG & (DEBUG_GAME): logging.info("Ship - Ship {} approached loiter assignment {} and it is friendly occupied by ship {}. Clearing assignment. t{}".format(ship.id, ship.assignments[-1], assignment_cell.ship.id, game.turn_number))
                        game.update_loiter_assignment(ship)
                        ship.path.pop()

        #
        # Move
        #
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
            elif ship.status == "tasked":
                # generally a ship should set it's status to a non-tasked status when it completes (what if there is another task?). In some
                # cases a task may leave the status as 'tasked' to preserve a move generated turn the task was completed.
                if not ship.tasks:
                    ship.status = "exploring"
                move = None
            elif ship.status == "homing":
                if ship.position == base_position:
                    move = "o"
                else:
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
        ship_states[ship.id]["tasks"] = ship.tasks
        ship_states[ship.id]["position"] = ship.position if move is None else get_position_from_move(game, ship, move)

        #
        # end for each ship
        #


    #
    # check of lost ships
    #
    lost_ships = []
    for s_id in ship_states:
        if not me.has_ship(s_id):
            lost_ships.append(s_id)

    base_list = get_base_positions(game)
    for s_id in lost_ships:
        lost_ship_position = ship_states[s_id]["position"]
        if not (lost_ship_position in base_list):
            sos_evt = {
                "s_id": s_id,
                "halite_amount": ship_states[s_id]["prior_halite_amount"],
                "position": lost_ship_position
            }
            game.sos_calls.append(sos_evt)

        if lost_ship_position in base_list:
            game_metrics["gathered"].append((ship_states[s_id]["last_seen"], s_id, ship_states[s_id]["prior_halite_amount"]))
            turn_gathered += ship_states[s_id]["prior_halite_amount"]
        else:
            if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} lost. Last seen at {} on turn {} with {} halite. t{}".format(s_id, ship_states[s_id]["prior_position"], ship_states[s_id]["last_seen"], ship_states[s_id]["prior_halite_amount"], game.turn_number))

        ship_states.pop(s_id, None)

    #
    # collect game metrics
    #
    turn_profit = turn_gathered - turn_spent
    cumulative_profit += turn_profit
    game_metrics["profit"].append((game.turn_number, turn_profit))
    game_metrics["turn_time"].append((game.turn_number, round(time.time() - turn_start_time, 4)))

    #
    # debug info for each turn
    #

    if DEBUG & (DEBUG_GAME_METRICS):
        mined_this_turn = sum(map(lambda i: i[2] if i[0] == game.turn_number else 0, game_metrics["mined"]))
        logging.info("Game - Mined this turn: {}".format(mined_this_turn))
        logging.info("Game - Turn mining rate: {}".format(0 if not len(my_ships) else round(mined_this_turn / len(my_ships), 2)))
        logging.info("Game - Mining rate: {}".format(round(game.get_mining_rate(), 2)))

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

        if DEBUG & (DEBUG_PROFILING):
            pr.disable()
            # To view results: ./analyze_stats.py profiler_results.dmp profiling_results.txt
            pr.dump_stats("profiler_results." + "{}".format(round(time.time())) + ".dmp")

        if DEBUG & (DEBUG_NAV_METRICS):
            logging.info("Nav  - Loiter multiples: {}".format(game_metrics["loiter_multiples"]))
            logging.info("Nav  - Loiter offsets: {}".format(game_metrics["loiter_offsets"]))
            logging.info("Nav  - Loiter distances: {}".format(game_metrics["loiter_distances"]))
            logging.info("Nav  - Raw loiter points: {}".format(game_metrics["raw_loiter_points"]))

        if DEBUG & (DEBUG_GAME_METRICS):
            avg_trip_duration = 0
            trip_explore_duration = 0
            trip_transit_duration = 0

            # trip_data 0:turn (end of trip) 1:ship 2:duration 3:halite 4:assigned loiter distance
            logging.info("Game - Total trips completed: {}".format(len(game_metrics["assn_duration"])))

            # all the keys below area
            if game_metrics["assn_duration"]:
                avg_trip_duration = round(np.mean(game_metrics["assn_duration"], axis=0)[2], 2)
                avg_trip_duration2 = round(np.mean(game_metrics["assn_duration2"], axis=0)[2], 2)
                logging.info("Game - Avg. trip duration: {} / ".format(avg_trip_duration, avg_trip_duration2))

            if game_metrics["assn_drop_amount"]:
                avg_halite_gathered = round(np.mean(game_metrics["assn_drop_amount"], axis=0)[3], 2)
                logging.info("Game - Avg. halite gathered: {}".format(avg_halite_gathered))

            if game_metrics["assn_explore_duration"]:
                # trip_explore_duration 0:turn (end of explore) 1:ship 2:duration 3:distance from base
                trip_explore_duration = round(np.mean(game_metrics["assn_explore_duration"], axis=0)[3], 2)
                logging.info("Game - Avg. explore duration: {}".format(trip_explore_duration))

            if game_metrics["assn_transit_duration"]:
                # trip_transit_duration 0:turn (end of return) 1:ship 2:duration 3:distance from base
                trip_transit_duration = round(np.mean(game_metrics["assn_transit_duration"], axis=0)[2], 2)
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

    # dump ship states after collision resolution
    if DEBUG & (DEBUG_SHIP_STATES): logging.info("Game - end ship_states:\n{}".format(ship_states_to_string(ship_states)))

    # check if we can spawn a ship. Make sure to check after all moves have been finalized
    if spawn_ok(game):
        if DEBUG & (DEBUG_GAME): logging.info("Game - Ship spawn request")
        game.command_queue[-1] = me.shipyard.spawn()

    #
    # max ship dropoff deployment
    #

    # must come after spawn_ok()
    if False and game.max_ships_reached == game.turn_number and not (current_dropoff_position is None):
        if DEBUG & (DEBUG_CV_MAP): logging.info("Queued dropoff deployment {}. t{}".format(current_dropoff_position, game.turn_number))
        dropoff_deployment_queue.append((current_dropoff_position, 0)) # dropofff = (deployment position, min_deploy_turn)

    if (DEBUG & (DEBUG_COMMANDS)): logging.info("Game - command queue: {}".format(game.command_queue))

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(list(game.command_queue.values()))


