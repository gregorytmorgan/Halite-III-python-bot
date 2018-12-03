#
# Mybot code
#

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Position
from hlt.positionals import Direction

from hlt.entity import Shipyard

import os
import time
import math
import random
import logging
import numpy as np

# mybot utils
from myutils.constants import *

def spawn_ok(game):
    """
    Is is possible to spawn a ship now?  Checks cost, collisions, ...

    :param game Game object
    :returns Returns True if a ship is spawnable
    """
    me = game.me
    shipyard = game.game_map[me.shipyard]

    # % turns above mining rate to dropoff the halite, will typically be about 2?
    mining_over_head = 2
    ship_count = len(me.get_ships())

    #
    # absolute constraints (order can be important)
    #

    if ship_count >= MAX_SHIPS:
        if DEBUG & (DEBUG_GAME): logging.info("GAME - Spawn denied. MAX ships reached".format())
        return False

    if me.halite_amount < constants.SHIP_COST:
        if DEBUG & (DEBUG_GAME): logging.info("GAME - Spawn denied. Insufficient halite".format())
        return False

    #
    # conditional constraints
    #

    # spawn 4 right away
    if EXPEDITED_DEPARTURE:
        if me.ship_count < EXPEDITED_SHIP_COUNT:
            if DEBUG & (DEBUG_GAME): logging.info("GAME - Spawn expedited due to ship count {} < {}".format(me.ship_count, EXPEDITED_SHIP_COUNT))
            return True

    # watch for collisions with owner only, note this will be 1 turn behind
    occupied_cells = []
    if shipyard.is_occupied and shipyard.ship.owner == me.id:
        occupied_cells.append(shipyard.position)

    # entry lane are N/S
    for pos in [shipyard.position.directional_offset(Direction.North), shipyard.position.directional_offset(Direction.North)]:
        if game.game_map[pos].is_occupied:
            occupied_cells.append(pos)

    # need to keep track of ships docking instead, a ship in an adjacent cell could be leaving
    if len(occupied_cells) > 0:
        if DEBUG & (DEBUG_GAME): logging.info("GAME - Spawn denied. Occupied cells: {}".format(occupied_cells))
        return False

    # primary constraint
    #
    # New code
    #
    #payback_turns = constants.SHIP_COST / get_mining_rate(game, MINING_RATE_LOOKBACK)
    #remaining_turns = constants.MAX_TURNS - game.turn_number
    #if payback_turns * mining_over_head < remaining_turns:
    #     if DEBUG & (DEBUG_GAME): logging.info("Spawn retval: {}".format(retval))
    #    return False
    #
    #return True

    ###
    ### v6 old code
    ###
    if me.ship_count > 0:
        payback_turns = constants.SHIP_COST / game.get_mining_rate(MINING_RATE_LOOKBACK)
        remaining_turns = constants.MAX_TURNS - game.turn_number

        retval = round(payback_turns * mining_over_head) < remaining_turns
        if DEBUG & (DEBUG_GAME): logging.info("Spawn retval: {}".format(retval))

        return retval
    else:
        return True

#
#
#
def get_max_loiter_distance(game):
    max_loiter_dist_x = min(game.me.shipyard.position.x, (game.game_map.width - game.me.shipyard.position.x))
    max_loiter_dist_y = min(game.me.shipyard.position.y, (game.game_map.height - game.me.shipyard.position.y))
    max_loiter_distance = min(max_loiter_dist_x, max_loiter_dist_y, MAX_LOITER)

    return float(max_loiter_distance)

#
#
#
def get_min_loiter_distance(game):
    # when a ship is sent off from the shipyard, this is the max distance.  It set
    # dynamically. The min loiter distance is stored as an offset, see min_loiter_distance
    return float(MIN_LOITER)

#
#
#
def get_loiter_multiple(game):

    # when a ship is sent off from the shipyard, this is the max distance it navigates
    # before 'exploring'
    min_loiter_distance = get_min_loiter_distance(game)

    #
    # stdist
    #
    # scipy lib is installed on server env by default
    #from scipy.stats import norm
    #
    # 0.3989422804014327 @ loc=0, scale=1.0
    # smaller number reduces tail flatness
    #inputWidth = 5.0
    #maxNorm = norm.pdf(0, loc=0, scale=1.0)
    #loiterMult = norm.pdf(inputWidth/2.0 - ((game.turn_number - 1)/constants.MAX_TURNS) * inputWidth, loc=0, scale=1.0)/maxNorm * maxLoiterDist

    #
    # atan
    #
    # inputOffset values shift curve left so we get into the steep part earlier
    #inputOffset = 75
    #
    # std value is pi? large inputWidth values result in 'more tail', small value move toward a strait line
    #inputWidth = math.pi * 2.0
    #
    #maxArcTan = math.atan(inputWidth - inputWidth/2) + math.atan(inputWidth/2)
    #loiterMult = math.atan(((game.turn_number - 1.0 + inputOffset)/constants.MAX_TURNS) * inputWidth - (inputWidth/2.0)) + math.atan(inputWidth/2.0)
    #loiterMult = loiterMult / maxArcTan * get_max_loiter_distance(game)

    #
    # linear
    #
    #loiterMult = (float(game.turn_number - 1) / float(constants.MAX_TURNS)) * get_max_loiter_distance(game)

    # based on area
    loiterMult = math.sqrt(game.turn_number - 1.0) / math.sqrt(constants.MAX_TURNS) * get_max_loiter_distance(game)

    # make sure we don't a useless mult
    if loiterMult < min_loiter_distance:
        loiterMult = min_loiter_distance

    return loiterMult

#
# type: 'random', 'density'
# collision_resolution: 'random', 'density', 'navigate'
#
#  waypoint_algorithm = "astar", args
#
def get_move(game, ship, type="random", args = None):
    """

    :param game
    :param ship
    :param type Type of move: 'nav'|'random'|'halite (density)'
    :param args    Args to accompany type
    """

    if not fuel_ok(game, ship):
        return "o"

    if DEBUG & (DEBUG_NAV): logging.info("Nav - ship {} Getting {} move ...".format(ship.id, type))

    if type == "random":
        move = get_random_move(game, ship, args)    # (game, ship, moves (optional))
    elif type == "density":
        move = get_halite_move(game, ship, args)    # (game, ship)
    elif type == "nav":
        move = get_nav_move(game, ship, args)       # (game, ship, {"waypoint_algorithm":"astar", "move_cost":"turns"}
    else:
        raise RuntimeError("Unknown move type: " + str(type))

    if DEBUG & (DEBUG_NAV): logging.info("Nav - ship {} Using {} move {}".format(ship.id, type, move))

    return move

def get_halite_move(game, ship, args = None):
    """
    Get a move based on the surrounding cell with the most halite

    :param args None ... for now. Add collision_resolution later
    """
    if args is None:
        args = {}

    move = "o"

    if DEBUG & (DEBUG_NAV): logging.info("Nav - ship {} is getting a density based move".format(ship.id))

    moves = []
    for quadrant in game.game_map.get_cell_block(ship.position, 3, 3):
        directional_offset = quadrant[0]
        block = quadrant[1]

        if block.get_max() > constants.MAX_HALITE * MINING_THRESHOLD_MULT:
            moves.append((directional_offset, block, block.get_mean()))

    sorted_blocks = sorted(moves, key=lambda item: item[2], reverse=True)

    if len(sorted_blocks) == 0:
        move = get_move(game, ship, "random") # ToDo: would be better to try a large search radius?
        if DEBUG & (DEBUG_NAV): logging.info("Nav - ship {} All surround have halite < {} . Returning random move: {}".format(ship.id, constants.MAX_HALITE * MINING_THRESHOLD_MULT, move))
        return move

    if DEBUG & (DEBUG_NAV): logging.info("Nav - ship {} found {} valid halite cells".format(ship.id, len(sorted_blocks)))

    best_bloc_data = sorted_blocks[0] # (directional_offset, block, block mean value)
    max_cell = best_bloc_data[1].get_max()

    for best_cell in best_bloc_data[1].get_cells():
        if best_cell.halite_amount == max_cell:
            break

    move_offset = best_bloc_data[0]
    if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} best cell moveOffset: {}".format(ship.id, move_offset))

    new_position = game.game_map.normalize(ship.position.directional_offset(move_offset))
    if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} best cell new_position: {}".format(ship.id, new_position))

    normalized_position = game.game_map.normalize(new_position)
    if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} best cell normalized_position: {}".format(ship.id, normalized_position))

    cell = game.game_map[normalized_position]

    #
    # collision resolution
    #
    if not cell.is_occupied:
        cell.mark_unsafe(ship)
        game.game_map[ship.position].mark_safe()
        move = Direction.convert(move_offset)
    else:
        logging.debug("ship {} collided with ship {} at {} while moving {}".format(ship.id, cell.ship.id, normalized_position, Direction.convert(move_offset)))

    # if we were not able to find a usable dense cell, try to find a random lateral one else still
    if move == "o":
        if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} best cell Collision A {}, trying to find a lateral move".format(ship.id, normalized_position))
        lateral_offsets = Direction.laterals(move_offset)
        lateral_moves = list(map(lambda direction_offset: Direction.convert(direction_offset), lateral_offsets))
        move = get_move(game, ship, "random", {"moves": lateral_moves})

    if move == "o":
        if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} Collision, unable to find a move".format(ship.id))

    # do this if move == "o" ?
    move_plus_one = Position(best_cell.position.x, best_cell.position.y) # go one more move in the same direction
    if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} has a move_plus_one of {}".format(ship.id, move_plus_one))
    ship.path.append(move_plus_one)

    return move

#
# nav moves resolv randomly
#
def get_random_move(game, ship, args = None):
    """
    Get a random move.

    :param args
        moves Array of moves to try. Default = ["n", "s", "e", "w"]
    :return Randomly tries to return a move from moves, if all produce collisions returns 'o'
    """

    if args is None:
        args = {}

    moves = args["moves"] if "moves" in args else ["n", "s", "e", "w"]

    if DEBUG & (DEBUG_NAV): logging.info("NAV - ship {} Getting random move with moves = {}".format(ship.id, moves))

    moveIdx = random.randint(1, len(moves))

    move = "o"

    for idx in range(moveIdx, moveIdx + len(moves)):
        moveChoice = moves[idx % len(moves)]
        if DEBUG & (DEBUG_NAV): logging.info("NAV - Ship {} moveChoice: {} {}".format(ship.id, idx, moveChoice))

        new_position = ship.position.directional_offset(DIRECTIONS[moveChoice])
        if DEBUG & (DEBUG_NAV): logging.info("NAV - Ship {} new_position: {}".format(ship.id, new_position))

        normalized_position = game.game_map.normalize(new_position)
        if DEBUG & (DEBUG_NAV): logging.info("NAV - Ship {} normalized_position {}".format(ship.id, normalized_position))

        cell = game.game_map[normalized_position]

        #
        # collision resolution
        #
        if not cell.is_occupied:
            cell.mark_unsafe(ship)
            game.game_map[ship.position].mark_safe()
            move = moveChoice
            break
        else:
            if DEBUG & (DEBUG_NAV): logging.info("ship {} collided with ship {} at {} while moving {}".format(ship.id, cell.ship.id, normalized_position, moveChoice))

    if DEBUG & (DEBUG_NAV): logging.info("NAV - ship {} getting random move {}".format(ship.id, move))

    return move

def get_nav_move(game, ship, args = None):
    """
    Get a move based on the exist ship.path

    :param game
    :param ship
    :param args
    :return Returns a move letter
    """

    if args is None:
        args = {}

    waypoint_resolution = args["waypoint_resolution"] if "waypoint_resolution" in args else "astar"
    move_cost = args["move_cost"] if "move_cost" in args else "turns"

    game_map = game.game_map

    if DEBUG & (DEBUG_NAV): logging.info("NAV - ship {} Getting nav move for path {} with waypoint resolution: {} and move_cost: {}".format(ship.id, ship.path, waypoint_resolution, move_cost))

    if not ship.path:
        if DEBUG & (DEBUG_NAV): logging.info("NAV - ship {} Getting nav path. Empty path. Returning 'o'".format(ship.id))
        return 'o'

    next_position = ship.path[-1]

     # check to see if we have a waypoint, not a continous path
    if game_map.calculate_distance(ship.position, next_position) > 1:
        normalized_next_position = game_map.normalize(next_position)

        if DEBUG & (DEBUG_NAV): logging.info("NAV - ship {} Getting nav path. Found waypoint {}, calulating complete path".format(ship.id, next_position))

        # calc a continous path
        path, cost = game_map.navigate(ship.position, normalized_next_position, waypoint_resolution, {"move_costs": move_cost})

        if path is None or len(path) == 0:
            if DEBUG & (DEBUG_NAV): logging.info("NAV - ship {} Nav failed, can't reach waypoint {} from {}".format(ship.id, normalized_next_position, ship.position))
            return 'o'
        else:
            if DEBUG & (DEBUG_NAV): logging.info("NAV - ship {} path to waypoint {} found with a cost of {} ({} turns)".format(ship.id, next_position, next_position, round(cost), len(path)))
            ship.path.pop()
            ship.path = ship.path + path

    new_position = ship.path[-1]
    if DEBUG & (DEBUG_NAV): logging.info("NAV - ship {} new_position: {}".format(ship.id, new_position))

    normalized_new_position = game_map.normalize(new_position)
    if DEBUG & (DEBUG_NAV): logging.info("NAV - ship {} normalized_new_position: {}".format(ship.id, normalized_new_position))

    # why?
    if normalized_new_position == ship.position:
        if DEBUG & (DEBUG_NAV): logging.warn("NAV - ship {} popped move {}. Returning 'o'.  Why?".format(ship.id, ship.path[-1]))
        ship.path.pop()
        return 'o'

    cell = game_map[normalized_new_position]

    # use get_unsafe_moves() to get a normalized directional offset. We should always get one soln.
    offset = game_map.get_unsafe_moves(ship.position, normalized_new_position)[0]
    move = Direction.convert(offset)

    if DEBUG & (DEBUG_NAV): logging.info("NAV - Ship {} has potential nav move: {}".format(ship.id, move))

    #
    # collision resolution
    #
    if not cell.is_occupied:
        cell.mark_unsafe(ship)
        game.game_map[ship.position].mark_safe()
        if DEBUG & (DEBUG_NAV): logging.info("NAV - ship {} popped nav path {}".format(ship.id, ship.path[-1]))
        ship.path.pop()
    else:
        # don't let enemy ships block the dropoff
        if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} collision with ship {} at {} while moving {}".format(ship.id, cell.ship.id, normalized_new_position, move))
        if cell.structure_type is Shipyard and cell.ship.owner != game.me.id:
            cell.mark_unsafe(ship)
            game.game_map[ship.position].mark_safe()
            ship.path.pop()

        # when arriving at a droppoff, wait from entry rather than making a random move
        # this probably will not work as well without entry/exit lanes
        elif game_map.calculate_distance(normalized_new_position, game.me.shipyard.position) == 1:
            move = "o"

        # when departing a shipyard, wait to leave
        elif ship.position == game.me.shipyard.position:
            move = "o"

#        elif ship.position == game.me.shipyard.position:
#            alternate_moves = Direction.laterals(move)
#            move = "o"
#            for alternate_move_offset in alternate_moves:
#                alternate_pos = ship.position.directional_offset(alternate_move_offset)
#                alternate_cell = game_map[alternate_pos]
#                if not alternate_cell.is_occupied:
#                    alternate_cell.mark_unsafe(ship)
#                    game.game_map[ship.position].mark_safe()
#                    move = Direction.convert(alternate_move_offset)
        else:
            move = get_move(game, ship, "random") # closest?
            if DEBUG & (DEBUG_NAV): logging.info("NAV - ship {} collision at {} with ship {}. Resolving to random move {}".format(ship.id, normalized_new_position, cell.ship.id , move))

    return move

def fuel_ok(game, ship):
    """
    Does the ship have enough fuel to move from the current cell?

    :param game
    :param ship
    :return Returns True if the ship has enough fuel to move, False otherwise.
    """
    fuelCost = game.game_map[ship.position].halite_amount * .1

    if round(fuelCost) > ship.halite_amount:
        if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} has insuffient fuel. Have {}, need {}".format(ship.id, ship.halite_amount, round(fuelCost, 2)))
        return False

    return True

#
#
#
def dump_stats(game, data, key = "all"):
    """
    Dump game stats to disk for analysis.

    :param game
    :param data The game data
    :param The data key
    :return None
    """
    if key == "all":
        keys = data.keys()
    else:
        keys = [key]

    ts = time.strftime("%Y%m%d-%s", time.gmtime())

    if os.path.exists(STATS_DIR):
        stats_dir = STATS_DIR
    else:
        stats_dir = "."

    for k in keys:
        with open(stats_dir + '/' + k + "-" + ts + "-bot-" + str(game.me.id) + ".log", "w") as f:
            for line in data[k]:
                f.write(str(line) + "\n")

def dump_data_file(game, data, file_basename):
    """
    Dump random data for debugging/analysis

    file_basename - no extension
    data - numpy array
    """

    ts = time.strftime("%Y%m%d-%s", time.gmtime())

    if os.path.exists(STATS_DIR):
        stats_dir = STATS_DIR
    else:
        stats_dir = "."

    np.set_printoptions(precision=1, linewidth=240, suppress=True, threshold=np.inf)

    data_str = np.array2string(data.astype(np.int64), separator=",")

    with open(stats_dir + '/' + file_basename + "-" + ts + "-bot-" + str(game.me.id) + ".log", "w") as f:
        f.write(data_str)

def should_move(game, ship):
    """
    Should the ship explore or mine?

    :param game
    :param ship
    :return Returns True is the ship should move/explore, False if the ship should mine.
    """
    cell_halite = game.game_map[ship.position].halite_amount

    if ship.is_full:
        return True

    if cell_halite < constants.MAX_HALITE * MINING_THRESHOLD_MULT:
        return True

#    cargo_threshold = .95 * constants.MAX_HALITE
#    logging.debug("DEBUG cargo {} > cargo threshold {} === {}".format(ship.halite_amount, cargo_threshold, ship.halite_amount > cargo_threshold))
#    if ship.halite_amount > cargo_threshold and ship.status == "returning":
#        return True

#    remaining_cargo_capacity = constants.MAX_HALITE - ship.halite_amount
#    mining_yield = cell_halite * .25
#    logging.debug("DEBUG {} >= {} === {}".format(mining_yield, remaining_cargo_capacity, mining_yield < remaining_cargo_capacity))
#    if mining_yield < remaining_cargo_capacity and ship.status == "returning":
#        return True

    return False

def get_loiter_point(game, ship, hint = None):
    """
    After a ship complets a dropoff, assign it a new destination whose distance is
    based on game number and direction is random

    1. get the loiter distance (multiplier)
    2. get a random point on a circle an mult by the loiter multiple
    3. extend the circle x,y by the loiter distance to create an offset
    4. Add the offset to the current position to get the loiter point
    5. Calc a nav path to the loiter point

    :param game
    :param ship
    :return Returns a position.
    """
    loiter_distance = get_loiter_multiple(game)

    if DEBUG & (DEBUG_NAV): logging.info("NAV - Ship {} loiter_distance: {}".format(ship.id, loiter_distance))
    if DEBUG & (DEBUG_NAV_METRICS): game.game_metrics["loiter_multiples"].append((game.turn_number, round(loiter_distance, 2)))

    # get a random point on a cicle in radians, note that +y is down
    if hint is None:
        pt = random.uniform(0, math.pi * 2)
    elif hint == "n":
        pt = random.uniform(7*math.pi/4, 5*math.pi/4)
    elif hint == "s":
        pt = random.uniform(3*math.pi/4, math.pi/4)
    elif hint == "e":
        pt = random.choice([random.uniform(7*math.pi/4, 2*math.pi), random.uniform(0, math.pi/4)])
    elif hint == "w":
        pt = random.uniform(5*math.pi/4, 3*math.pi/4)
    else:
        raise

    raw_loiter_point = (math.cos(pt), math.sin(pt))

    if DEBUG & (DEBUG_NAV): logging.info("NAV - Ship {} raw_loiter_point: ({},{}), loiter_distance: {}, hint: {}".format(ship.id, round(raw_loiter_point[0], 4), round(raw_loiter_point[1], 4), loiter_distance, hint))

    loiterOffset = Position(round(raw_loiter_point[0] * loiter_distance), round(raw_loiter_point[1] * loiter_distance))

    if DEBUG & (DEBUG_NAV_METRICS): game.game_metrics["raw_loiter_points"].append(raw_loiter_point)
    if DEBUG & (DEBUG_NAV_METRICS): game.game_metrics["loiter_offsets"].append((loiterOffset.x, loiterOffset.y))

    return ship.position + loiterOffset

def get_departure_point(game, dropoff, destination, departure_lanes = "e-w"):
    """
    Get the first position for a departing ship.

    :param game
    :param dropoff Position
    :param destination Position
    :param departure_lanes "n-s" | "e-w", default = "e-w"
    """
    distance = abs(destination - dropoff)

    shortcut_x = True if distance.x >= (game.game_map.width / 2) else False
    shortcut_y = True if distance.y >= (game.game_map.height / 2) else False

    if departure_lanes == "e-w":
        departure_distance = -DEPARTURE_DISTANCE if shortcut_x else DEPARTURE_DISTANCE
        departure_x = dropoff.x + departure_distance if destination.x > dropoff.x else dropoff.x - departure_distance
        departure_y = dropoff.y
    elif departure_lanes == "n-s":
        departure_distance = -DEPARTURE_DISTANCE if shortcut_y else DEPARTURE_DISTANCE
        departure_x = dropoff.x
        departure_y = dropoff.y + departure_distance if destination.y > dropoff.y else dropoff.y - departure_distance
    else:
        raise RuntimeError("Unknown departure_lanes: " + str(departure_lanes))

    return Position(departure_x, departure_y)

def get_dropoff_position(game, ship):
    """
    Get the closest dropoff or shipyard to ship

    :param game
    :param ship
    :return Returns a position
    """
    dropoffs = game.me.get_dropoffs()
    destinations = list(dropoffs) + [game.me.shipyard.position]

    minDistance = False
    movePosition = False

    for dest in destinations:
        distance = game.game_map.calculate_distance(ship.position, dest)
        if minDistance == False or distance < minDistance:
            minDistance = distance
            movePosition = dest

    return movePosition

#
# destination - The direction the ship is trying to go.  Backoff will be opposite
#
def get_backoff_point(game, ship, destination):
    destinationMoves = game.game_map.get_unsafe_moves(ship.position, destination)

    if len(destinationMoves) == 0:
        return ship.position

    choice = random.choice(destinationMoves)
    backoffDirection = Direction.invert(choice)

    # when there's a collion, we backoff between 1 and nShips/2 cells
    mult = random.randint(1, max(1, round(len(game.me.get_ships()) / 2)))

    backoffPoint = ship.position + Position(backoffDirection[0] * mult, backoffDirection[1] * mult)

    # if the backup point wrap, truncate it to the edge to prevent simple nav from failing
    if backoffPoint.x > game.game_map.width - 1:
        backoffPoint.x = game.game_map.width - 1

    if backoffPoint.x < 0:
        backoffPoint.x = 0

    if backoffPoint.y > game.game_map.height - 1:
        backoffPoint.y = game.game_map.height - 1

    if backoffPoint.y <    0:
        backoffPoint.y = 0

    if DEBUG & (DEBUG_NAV): logging.info("Nav.get_backoff_point() - ship {} has backoffPoint {}".format(ship.id, backoffPoint))

    return backoffPoint