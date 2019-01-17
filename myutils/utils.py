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

from myutils.cell_block import CellBlock

def spawn_ok(game):
    """
    Is is possible to spawn a ship now?  Checks cost, collisions, ...

    :param game Game object
    :returns Returns True if a ship is spawnable
    """
    me = game.me
    shipyard_cell = game.game_map[me.shipyard]
    ship_count = len(me.get_ships())
    player_count = len(game.players)

    if player_count == 2 and game.game_map.width in [56, 64]:
        mining_overhead = MINING_OVERHEAD_OPEN
    elif player_count == 4 and game.game_map.width in [32, 40]:
        mining_overhead = MINING_OVERHEAD_CONGESTED
    else:
        mining_overhead = MINING_OVERHEAD_DEFAULT

    #
    # absolute constraints (order can be important)
    #

    # always return False if we don't have enough halite
    if me.halite_amount < constants.SHIP_COST:
        if DEBUG & (DEBUG_GAME): logging.info("Game - Spawn denied. Insufficient halite".format())
        return False

    # watch for collisions with friendly ships only, spawn on enemy ship to clear the base.
    occupied_cells = []
    if shipyard_cell.is_occupied and shipyard_cell.ship.owner == me.id:
        occupied_cells.append(shipyard_cell.position)

    # entry lane are N/S
    for pos in [shipyard_cell.position.directional_offset(Direction.North), shipyard_cell.position.directional_offset(Direction.South)]:
        if game.game_map[pos].is_occupied and game.game_map[pos].ship.owner == me.id:
            occupied_cells.append(pos)

    if occupied_cells:
        if DEBUG & (DEBUG_GAME): logging.info("Game - Spawn denied. Occupied cells: {}".format(occupied_cells))
        return False

    # Attention: This short-circuits (is before) some other conditions by design
    # check base_clear_request after occupied_cells since we don't need to spawn when a ship is arriving
    if game.base_clear_request:
        clear_request = game.base_clear_request[-1]
        if DEBUG & (DEBUG_GAME): logging.info("Game - Spawning to clear blocked base {}".format(clear_request["position"]))
        return True

    if game.fund_dropoff:
        return False

    if game.end_game:
        return False

    #
    # conditional constraints
    #

    # conditions above that return True do not respect MAX_SHIPS by design
    if ship_count >= MAX_SHIPS:
        if DEBUG & (DEBUG_GAME): logging.info("Game - Spawn denied. MAX ships reached".format())
        return False

    # primary constraint
    #
    # New code
    #
    #payback_turns = constants.SHIP_COST / game.get_mining_rate()
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
        payback_turns = constants.SHIP_COST / game.get_mining_rate()
        remaining_turns = constants.MAX_TURNS - game.turn_number
        retval = round(payback_turns * mining_overhead) < remaining_turns
        if DEBUG & (DEBUG_GAME): logging.info("Spawn retval: {}, payback: {}*{} < {}".format(retval, round(payback_turns, 2), mining_overhead, remaining_turns))

        if not retval and not game.max_ships_reached:
            if DEBUG & (DEBUG_GAME): logging.info("Game - Peak ships reached at t{}".format(game.turn_number))
            game.max_ships_reached = game.turn_number

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
    Get a move

    :param game
    :param ship
    :param type Type of move: 'nav'|'random'|'halite (density)'
    :param args Args to accompany type
    :returns Returns a move letter on success, None if there is a collision.
    """

    if not fuel_ok(game, ship):
        return "o"

    if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} Getting {} move ...".format(ship.id, type))

    if type == "random":
        move = get_random_move(game, ship, args)    # (game, ship, moves (optional))
    elif type == "density":
        move = get_halite_move(game, ship, args)    # (game, ship)
    elif type == "nav":
        move = get_nav_move(game, ship, args)       # (game, ship, {"waypoint_algorithm":"astar", "move_cost":"turns"}
    else:
        raise RuntimeError("Unknown move type: {}".format(type))

    if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} Using {} move {}".format(ship.id, type, move))

    # mark safe if we move or have a collision (we'll resolve the collision later). This allows other ships
    # to move to this ship old position.
    if move != "o":
        game.game_map[ship.position].mark_safe()

    return move

def get_best_blocks(game, ship, w, h):
    """
    Get the surrounding cell blocks

    :param game
    :param ship
    :returns Returns a list of cell blocks, sorted by halite
    """
    best_blocks = []
    for blocks in game.game_map.get_cell_blocks(ship.position, w, h): # returns list of tuples [(direction), CellBlock]
        directional_offset = blocks[0]
        block = blocks[1]

        has_base = True if block.contains_position(get_base_positions(game, ship.position)) else False

        if block.get_max() > ship.mining_threshold and not has_base:
            best_blocks.append((directional_offset, block, block.get_mean()))

    return sorted(best_blocks, key=lambda item: item[2], reverse=True)

def get_halite_move(game, ship, args = None):
    """
    Get a move based on the surrounding cell with the most halite

    :param args None ... for now.
    :returns Returns a move letter on success, None if there is a collision.
    """
    if args is None:
        args = {}

    move = "o"

    if DEBUG & (DEBUG_NAV_VERBOSE): logging.info("Nav  - Ship {} is getting a density based move".format(ship.id))

    sorted_blocks = get_best_blocks(game, ship, 3, 3)

    if not sorted_blocks:
        old_threshold = ship.mining_threshold
        ship.mining_threshold = 25
        if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} Best block search failed 1.  All surrounding cells have halite < threshold({}). Setting mining_threshold to {} and retrying. t{}".format(ship.id, old_threshold, ship.mining_threshold, game.turn_number))
        sorted_blocks = get_best_blocks(game, ship, 3, 3)
        if not sorted_blocks:
            move = get_random_move(game, ship) # ToDo: would be better to try a large search radius?
            if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} Best block search failed 2. All surrounding cells have halite < threshold({}) . Returning random move: {}. t{}".format(ship.id, ship.mining_threshold, move, game.turn_number))
            return move

    best_bloc_data = sorted_blocks[0] # (directional_offset, block, block mean value)
    max_cell_amount = best_bloc_data[1].get_max()

    if DEBUG & (DEBUG_NAV_VERBOSE): logging.info("Nav  - Ship {} found {} valid halite cells with a the max cell containing {} halite".format(ship.id, len(sorted_blocks), max_cell_amount))

    for best_cell in best_bloc_data[1].get_cells():
        if best_cell.halite_amount == max_cell_amount:
            break

    move_offset = best_bloc_data[0]

    new_position = game.game_map.normalize(ship.position.directional_offset(move_offset))

    normalized_position = game.game_map.normalize(new_position)

    cell = game.game_map[normalized_position]

    if DEBUG & (DEBUG_NAV_VERBOSE): logging.info("Nav  - Ship {} next cell: {}, offset: {}, value: {}".format(ship.id, normalized_position, move_offset, cell.halite_amount))

    #
    # collision resolution
    #
    if cell.is_occupied:
        game.collisions.append((ship, cell.ship, Direction.convert(move_offset), normalized_position, resolve_halite_move)) # args = alt moves?
        if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} collided with ship {} at {} while moving {}".format(ship.id, cell.ship.id, normalized_position, Direction.convert(move_offset)))
        return None

    #
    # success
    #
    cell.mark_unsafe(ship)
    move = Direction.convert(move_offset)

    # blocks are guaranteed to have at least 1 cell that is minable. This is critical to avoid getting stuck
    # between two blocks each of which is never modified.  For a 3x3 block, add 'plus_one' assures that we move
    # far enough to reach the modifiable cell, thus preventing an endless movement between blocks
    move_plus_one = Position(best_cell.position.x, best_cell.position.y) # go one more move in the same direction
    if cell.position != move_plus_one:
        if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} has a plus_one move of {}, halite: {}".format(ship.id, move_plus_one, max_cell_amount))
        ship.path.append(move_plus_one)

    return move

#
# nav moves resolv randomly
#
def get_random_move(game, ship, args = None):
    """
    Get a random move. Randomly tries to return a move from moves. Returns None on collision.

    :param args
        moves Array of moves to try. Default = ["n", "s", "e", "w"]
    :returns Returns a move letter on success, None if there is a collision.
    """

    if args is None:
        args = {}

    moves = args["moves"] if "moves" in args else ["n", "s", "e", "w"]
    if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} Getting random move with moves = {} ... ".format(ship.id, moves))

    move = random.choice(moves)
    if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} move: {}".format(ship.id, move))

    new_position = ship.position.directional_offset(DIRECTIONS[move])
    if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} new_position: {}".format(ship.id, new_position))

    normalized_position = game.game_map.normalize(new_position)
    if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} normalized_position {}".format(ship.id, normalized_position))

    cell = game.game_map[normalized_position]

    #
    # collision resolution
    #
    if cell.is_occupied:
        remaining_moves = [x for x in moves if move not in x]
        if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} collided with ship {} at {} while moving {}. Remaining_moves: {}".format(ship.id, cell.ship, normalized_position, move, remaining_moves))

        game.collisions.append((ship, cell.ship, move, normalized_position, resolve_random_move)) # args = remaining moves
        return None

    #
    # success
    #
    cell.mark_unsafe(ship)
    if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} Getting random move {}".format(ship.id, move))

    return move

def get_nav_move(game, ship, args = None):
    """
    Get a move based on the exist ship.path

    :param game
    :param ship
    :param args
    :returns Returns a move letter on success, None if there is a collision.
    """

    if args is None:
        args = {}

    # hack - shouldn't need to do this
    while ship.path:
        if game.game_map.normalize(ship.path[-1]) == ship.position:
            logging.warn("Nav  - Ship {} popped move {}.  Why did this happen?".format(ship.id, ship.path[-1]))
            ship.path.pop()
        else:
            break

    waypoint_resolution = args["waypoint_resolution"] if "waypoint_resolution" in args else "astar"
    move_cost = args["move_cost"] if "move_cost" in args else "turns"

    game_map = game.game_map

    if DEBUG & (DEBUG_NAV_VERBOSE): logging.info("Nav  - Ship {} Getting nav move, path: {}, waypoint resolution: {}, move_cost: {}".format(ship.id, list_to_short_string(ship.path, 4), waypoint_resolution, move_cost))

    ship_cell = game_map[ship]

    if not ship.path:
        logging.warn("Nav  - Ship {} Getting nav path. Empty path. Returning 'o'. t{}".format(ship.id, game.turn_number))
        ship_cell.mark_unsafe(ship)
        return 'o'

    next_position = ship.path[-1]

     # check to see if we have a waypoint, not a continous path
    if game_map.calculate_distance(ship.position, next_position) > 1:
        normalized_next_position = game_map.normalize(next_position)

        if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} Getting nav path. Found waypoint {}, calulating complete path".format(ship.id, next_position))

        # calc a continous path
        path, cost = game_map.navigate(ship.position, normalized_next_position, waypoint_resolution, {"move_costs": move_cost})

        if path is None or len(path) == 0:
            logging.warn("Nav  - Ship {} Nav failed, can't reach waypoint {} from {}".format(ship.id, normalized_next_position, ship.position))
            if ship_cell.is_occupied:
                game.collisions.append((ship, ship_cell.ship, 'o', ship.position, resolve_nav_move)) # args = ?
                if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} collided with ship {} at {} while moving {}".format(ship.id, ship_cell.ship.id, ship.position, 'o'))
                return None
            else:
                ship_cell.mark_unsafe(ship)
                return 'o'
        else:
            if DEBUG & (DEBUG_NAV_VERBOSE): logging.info("Nav  - Ship {} path to waypoint {} found. Length: {}, cost: {}".format(ship.id, next_position, len(path), round(cost)))
            ship.path.pop()
            ship.path = ship.path + path

    new_position = ship.path[-1]

    normalized_new_position = game_map.normalize(new_position)
    if DEBUG & (DEBUG_NAV_VERBOSE): logging.info("Nav  - Ship {} new_position: {}".format(ship.id, normalized_new_position))

    cell = game_map[normalized_new_position]

    # use get_unsafe_moves() to get a normalized directional offset. We should always get one soln.
    offset = game_map.get_unsafe_moves(ship.position, normalized_new_position)[0]
    move = Direction.convert(offset)

    if DEBUG & (DEBUG_NAV_VERBOSE): logging.info("Nav  - Ship {} has potential nav move: {}".format(ship.id, move))

    #
    # collision resolution
    #
    if cell.is_occupied:
        game.collisions.append((ship, cell.ship, move, normalized_new_position, resolve_nav_move)) # args = ?
        if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} collided with ship {} at {} while moving {}".format(ship.id, cell.ship.id, normalized_new_position, move))
        return None

    #
    # success
    #
    cell.mark_unsafe(ship)
    if DEBUG & (DEBUG_NAV_VERBOSE): logging.info("Nav  - Ship {} popped nav path {}".format(ship.id, ship.path[-1]))
    ship.path.pop()

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

    :param game
    :param data Numpy array
    :param file_basename No extension
    :returns None
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

def move_ok(game, ship, args = None):
    """
    Should the ship explore or mine?

    Note: The refueling case is handled by the get_move code.

    :param game
    :param ship
    :returns Returns True is the ship should move/explore, False if the ship should mine.
    """

    if args is None:
        args = {}

    cell_halite = game.game_map[ship.position].halite_amount

    if ship.status == "homing":
        return True

    if ship.is_full:
        return True

    # generally ignore low value cells.
    if cell_halite <= ship.mining_threshold:
        return True

    fuel_status = ship.halite_amount / SHIP_MAX_HALITE

    # the amount of halite we'll get if we refuel/mine
    # if ship in a base (dropoff/shipyard), set fuel to max to the ship departs
    # refuel_amount = constants.MAX_HALITE if ship.position in base else cell_halite * SHIP_MINING_EFFICIENCY

    net_mine = (cell_halite * SHIP_MINING_EFFICIENCY) + (cell_halite - cell_halite * SHIP_MINING_EFFICIENCY) * -SHIP_FUEL_COST
    net_move = cell_halite * -SHIP_FUEL_COST + game.get_mining_rate() * SHIP_MINING_EFFICIENCY

    #logging.debug("fuel_status: {}".format(fuel_status))
    #logging.debug("refuel_amount: {}".format(refuel_amount))
    #logging.debug("net_mine: {}, net_move: {}".format(net_mine, net_move))

    if ship.status == "transiting":
        #if refuel_amount > net_mining_yield and fuel_status < SHIP_REFUEL_THRESHOLD:
        #    return True
        pass
    elif ship.status == "exploring":
        #if cell_halite < ship.mining_threshold:
        #    return True
        pass
    elif ship.status == "returning":
        if net_move > net_mine or fuel_status > SHIP_REFUEL_THRESHOLD:
            return True
    elif ship.status == "tasked":
        return True # don't prevent a tasked ship from moving
    else:
        raise RuntimeError("Unknown ship status: {}".format(ship.status))

    return False

def get_loiter_point(game, ship, hint = None):
    """
    After a ship complets a drop, assign it a new destination whose distance is
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

    if DEBUG & (DEBUG_NAV_VERBOSE): logging.info("Nav  - Ship {} loiter_distance: {}".format(ship.id, loiter_distance))
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
        raise RuntimeError("Unknown hint: {}".format(hint))

    raw_loiter_point = (math.cos(pt), math.sin(pt))

    if DEBUG & (DEBUG_NAV_VERBOSE): logging.info("Nav  - Ship {} raw_loiter_point: ({},{}), loiter_distance: {}, hint: {}".format(ship.id, round(raw_loiter_point[0], 4), round(raw_loiter_point[1], 4), loiter_distance, hint))

    loiterOffset = Position(round(raw_loiter_point[0] * loiter_distance), round(raw_loiter_point[1] * loiter_distance))

    if DEBUG & (DEBUG_NAV_METRICS): game.game_metrics["raw_loiter_points"].append(raw_loiter_point)
    if DEBUG & (DEBUG_NAV_METRICS): game.game_metrics["loiter_offsets"].append((loiterOffset.x, loiterOffset.y))

    return ship.position + loiterOffset

def get_departure_point(game, base_position, destination, departure_lanes = "e-w"):
    """
    Get the first position for a departing ship.

    :param game
    :param base_position Position
    :param destination Position
    :param departure_lanes "n-s" | "e-w", default = "e-w"
    :return Returns a position
    """
    distance = abs(destination - base_position)

    shortcut_x = True if distance.x >= (game.game_map.width / 2) else False
    shortcut_y = True if distance.y >= (game.game_map.height / 2) else False

    std_departure_distance = 1 if game.game_map.calculate_distance(base_position, destination) <= DEPARTURE_DISTANCE else DEPARTURE_DISTANCE

    if departure_lanes == "e-w":
        departure_distance = -std_departure_distance if shortcut_x else std_departure_distance
        departure_x = base_position.x + departure_distance if destination.x > base_position.x else base_position.x - departure_distance
        departure_y = base_position.y
    elif departure_lanes == "n-s":
        departure_distance = -std_departure_distance if shortcut_y else std_departure_distance
        departure_x = base_position.x
        departure_y = base_position.y + departure_distance if destination.y > base_position.y else base_position.y - departure_distance
    else:
        raise RuntimeError("Unknown departure_lanes: " + str(departure_lanes))

    return Position(departure_x, departure_y)

def get_base_positions(game, position = None):
    """
    Get the closest base (dropoff or shipyard) from position.

    If position is None, get all bases.

    :param game
    :param position
    :return Returns a single position if the position arg is provded, returns an list of all base positions otherwise.
    """
    base_positions = [game.me.shipyard.position]

    for do in game.me.get_dropoffs():
        base_positions.append(do.position)

    if position is None:
        return base_positions

    min_distance = False
    closest_base = False

    for base_position in base_positions:
        distance = game.game_map.calculate_distance(position, base_position)
        if closest_base is False or distance < min_distance:
            min_distance = distance
            closest_base = base_position

    return closest_base

#
# Collision Resolution
#
# The collision resolution sequence is:
#    0. Ships are sorted/processed by halite amount.
#    1. Attempt a move
#    2. If the move causes a collision, add a collision tupple to the game collision list. The
#       tuple constains a 'resolver'.
#    3. After all ship have attempted to move, iterate over the collisions calling the resolver
#       for each.
#    4. If the resolver fails (return None), attempt to place the colliding ship in it's original
#       position (move == 'o'), if that position is occuplied then call unwind() on the colliding
#       ships position.
#
# Collision resolution is generally composed three elements:
#    1. The collision resolution method. This method loops thru all collisions and calls the
#       provided resolver for each. It the resolver can not find a satifactory move, it should
#       return None, this will trigger unwind().
#    2. A 'resolver' for each move type called from get_move(). The resolver is passed as
#       part of the collision tuple if the initial move causes a collision.
#    3. unwind(). When the collision resolver fails, the colliding ship remains in it's original
#       position. It is possible the another ship has moved into that position expecting the
#       ship to move. In this case moves are unwound intil a ship can remain in it's position.
#

def resolve_collsions(game, ship_states):
    """
    Resolve all collisions in the collision list

    :param game
    :param ship_states Pass in the states so we can update the blocked_by attrib
    :return None
    """
    game_map = game.game_map

    if DEBUG & (DEBUG_GAME): logging.info("Game - Collision resolution start. {} collisions need resolution".format(len(game.collisions)))

    # for each collision identify type and resolve, then add solved move to the command queue
    for collision in game.collisions:
        # 0:ship1 1:ship2 2:move 3:dest1 4:res_func
        ship1 = collision[0]
        ship2 = collision[1]
        direction = collision[2]
        collision_cell = game_map[collision[3]]
        resolver = collision[4]

        if not collision_cell.is_occupied:
            if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} - not occupied: moving {} to {} previously collided with ship {}".format(ship1.id, direction, collision_cell.position, ship2.id))
            move = direction
            collision_cell.mark_unsafe(ship1)
            if ship1.path and collision_cell.position == ship1.path[-1] and collision_cell.position != get_base_positions(game, ship1.position):
                ship1.path.pop()
        else:
            blocked_by_move = get_blocked_by_move(game, collision)
            ship_states[ship1.id]["blocked_by"] = ship1.blocked_by

            if blocked_by_move is not None:
                move = blocked_by_move
            else:
                if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} - calling provided resolver: moving {} to {} collided with ship {}, resolving ...".format(ship1.id, direction, collision_cell.position, ship2.id))
                move = resolver(game, collision) # will all res functions have the same prototye/signature? Should they be lambdas?

            if move is None:
                # resolver failed, if original cell is occupied then unwind, else reclaim old cell
                if game_map[ship1].is_occupied:
                    cnt = unwind(game, ship1, ship_states)
                    if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} collision resolved by unwinding {} ships".format(ship1.id, cnt))
                else:
                    game_map[ship1].mark_unsafe(ship1)

                move = 'o'
            else:
                cell = game_map[ship1.position.directional_offset(move)]
                cell.mark_unsafe(ship1)

            if DEBUG & (DEBUG_NAV): logging.info("Nav  - Collision resolved: ship {} resolving to {}".format(ship1.id, move))

        game.command_queue[ship1.id] = ship1.move(move)
        ship_states[ship1.id]["position"] = get_position_from_move(game, ship1, move)

        if ship1.assignments and ship1.assignments[-1] == ship1.position and move != "o":
            if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} completed assignment {}, clearing assignment.".format(ship1.id, ship1.assignments[-1]))
            game.update_loiter_assignment(ship1)

    if DEBUG & (DEBUG_GAME): logging.info("Game - Collision resolution complete")

    return None

def get_backoff_point(game, ship, destination):
    """
    Get a nav position in the opposite direction of travel a random number of cells away

    Currently the backoff distance is a function of ship count.

    This function isn't currently used

    :param game
    :param ship
    :return Return a position n cells away with an inverse direction.
    """
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

    if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} has backoffPoint {}".format(ship.id, backoffPoint))

    return backoffPoint


def get_blocked_by_move(game, collision):
    """
    Make sure the same ship is repeatedly blocking us

    :param game
    :param collision Collision tuple: (0:ship1 1:ship2 2:move 3:dest1 4:res_func)
    :return Return a 'crash move' is the ship has been blocked too long. None otherwise.
    """

    ship1 = collision[0]
    ship2 = collision[1]
    move = collision[2]
    position = collision[3]
    #cell = game.game_map[position]

    if not ship1.blocked_by:
        ship1.blocked_by = {"ship": ship2, "turns": 1}
        if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} is now blocked by ship {} at {}.".format(ship1.id, ship2.id, position))
        return None

    turns_blocked = ship1.blocked_by["turns"]
    blocker = ship1.blocked_by["ship"]
    if ship1.owner == game.me.id:
        block_threshold = BLOCKED_BY_THRESHOLD_FRIENDLY
    else:
        block_threshold = BLOCKED_BY_THRESHOLD

    # cell.ship.id == ship2.id and
    if blocker.id == ship2.id and blocker.position == ship2.position and turns_blocked >= block_threshold:
        if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} has been blocked by ship {} at {} for {} turns. Crashing".format(ship1.id, ship2.id, position, turns_blocked))
        game.game_map[position].mark_unsafe(ship1)
        if ship1.path:
            ship1.path.pop()
        return move
    elif blocker.id == ship2.id and blocker.position == ship2.position:
        turns_blocked += 1
        ship1.blocked_by = {"ship": ship2, "turns": turns_blocked}
        if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} has been blocked by ship {} at {} for {} turns. Waiting.".format(ship1.id, ship2.id, position, turns_blocked))
    else:
        ship1.blocked_by = {"ship": ship2, "turns": 1}
        if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} is now blocked by ship {} at {}".format(ship1.id, ship2.id, position))

    return None

def resolve_random_move(game, collision, args = None):
    """
    Resolve a random move.

    :param game
    :param collision Collision tuple: (0:ship1 1:ship2 2:move 3:dest1 4:res_func)
    :returns Returns the first viable random move excluding the original collision move.
        Returns None if no move exists.
    """
    ship = collision[0]

    if args is None:
        args = {}

    moves = args["moves"] if "moves" in args else ["n", "s", "e", "w"]

    if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} - Resolving random move collision ..., moves = {}".format(ship.id, moves))

    moveIdx = random.randint(1, len(moves))

    move = None

    for idx in range(moveIdx, moveIdx + len(moves)):
        moveChoice = moves[idx % len(moves)]
        if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} moveChoice: {} {}".format(ship.id, idx, moveChoice))

        new_position = ship.position.directional_offset(moveChoice)
        if DEBUG & (DEBUG_NAV_VERBOSE): logging.info("Nav  - Ship {} new_position: {}".format(ship.id, new_position))

        normalized_position = game.game_map.normalize(new_position)
        if DEBUG & (DEBUG_NAV_VERBOSE): logging.info("Nav  - Ship {} normalized_position {}".format(ship.id, normalized_position))

        cell = game.game_map[normalized_position]

        #
        # collision resolution
        #
        if not cell.is_occupied:
            cell.mark_unsafe(ship)
            move = moveChoice
            break
            if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} - Successfully resolved random move collision. Move: {}".format(ship.id, move))
        else:
            if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} - Failed to resolved random move collision. Move: {}".format(ship.id, move))

    return move

def resolve_halite_move(game, collision):
    """
    Resolve collisions for a halite move.

    :param game
    :param collision Collision tuple: (0:ship1 1:ship2 2:move 3:dest1 4:res_func)
    :returns Returns the 'o' or the lateral move based on the one with the most halite on success. 'o' gets
        a 10% preference. Returns None if unable to resolve.
    """

    ship = collision[0]
    move = collision[2]
    #position = collision[3]

    if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} - Resolving density move".format(ship.id))

    # possible moves are left, right, still, back
    move_offsets = Direction.laterals(DIRECTIONS[move]) + [Direction.Still] + [Direction.invert(DIRECTIONS[move])]

    best_moves = []
    for o in move_offsets:
        pos = ship.position.directional_offset(o)
        cell = game.game_map[pos]

        if o == Direction.Still:
            val = cell.halite_amount * 1.1    # staying gets a bonus 10%
        elif o == Direction.invert(DIRECTIONS[move]):
            val = cell.halite_amount * .5    # going backwards is less desirable
        else:
            val = cell.halite_amount

        best_moves.append((cell, val, o))

    best_moves.sort(key=lambda item: item[1], reverse=True)

    new_offset = None
    new_cell = None

    # try the cells to the left/right of the direction orginally attempted in order of
    # desirability. Additionally check staying still.
    for m in best_moves:
        if not m[0].is_occupied:
            new_offset = m[2]
            new_cell = m[0]
            break;

    # if no cell is available then the ship lost it's original cell, and the two lateral moves are
    # blocked, try the only remaining option, the inverse of the original, otherwise rewind
    if new_offset is None:
        move = None
    else:
        if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} - Resolved by best cell {}".format(ship.id, new_cell.position))
        new_cell.mark_unsafe(ship)
        move = Direction.convert(new_offset)

    if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} - Successfully resolved density move collision. Move: {}".format(ship.id, move))

    return move

def resolve_nav_move(game, collision):
    """
    Resolve a nav move.

    Note: The current position of the ship is 'given up'/marked safe for others in get_move(),
    there is no guarantee the ship can remain in it's current position - be sure to check is_occupied
    for the current cell if returning 'o'

    Note: before this method is called, a blocked by n turns chk takes place.

    If we don't find a special case solution, the default is a random lateral move.

    :param game
    :param collision Collision tuple: (0:ship1 1:ship2 2:move 3:dest1 4:res_func)
    :returns Returns move based on a number of special cases, if none of these exists,
        returns a random move excluding the original collision move. Returns 'o' if no
        move exists.
    """

    ship1 = collision[0]
    ship2 = collision[1]
    move = collision[2]
    position = collision[3]

    collision_cell = game.game_map[position]
    ship_cell = game.game_map[ship1]

    if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} - Resolving nav move".format(ship1.id))

    if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} collided with ship {} at {} while moving {}".format(ship1.id, ship2.id, position, move))

    arrival_points = [game.me.shipyard.position.directional_offset(Direction.North), game.me.shipyard.position.directional_offset(Direction.South)]

    # don't let enemy ships on a dropoff/shipyard block arrivals or spawns. Halite from both ships will be deposited
    if collision_cell.structure_type is Shipyard and collision_cell.ship.owner != game.me.id:
        if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} collided with enemy ship {} at shipyard. Crashing".format(ship1.id, ship2.id))
        collision_cell.mark_unsafe(ship1)
        ship1.path.pop()
        new_move = move

    elif collision_cell.position in get_base_positions(game) and game.end_game:
        if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} collided with ship {} at shipyard during end game. Crashing".format(ship1.id, ship2.id))
        collision_cell.mark_unsafe(ship1)
        new_move = move

    elif ship2.position == collision_cell.position and ship2.owner != game.me.id and collision_cell.position in get_base_surrounding_cardinals(game, ship1.position):
        game.base_clear_request.insert(0, {"position": collision_cell.position, "ship": ship2}) # , "base": base

        if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} sent a base clear request for {}. Blocked by {}".format(ship1.id, collision_cell.position, ship2.id))

        if game.game_map[ship1].is_occupied:
            new_move = None # None == unwind
        else:
            ship_cell.mark_unsafe(ship1)
            new_move = "o"

    # when arriving at a droppoff, wait from entry rather than making a move
    # this probably will not work as well without entry/exit lanes
    elif ship1.path and ship1.path[0] == game.me.shipyard.position and ship1.position in arrival_points:
        if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} is close to base, waiting ...".format(ship1.id))
        if game.game_map[ship1].is_occupied:
            new_move = None # None == unwind
        else:
            ship_cell.mark_unsafe(ship1)
            new_move = "o"

    # when departing ...
    elif ship1.position == game.me.shipyard.position:
        # wait zero for enemy
        if collision_cell.ship.owner != game.me.id:
            collision_cell.mark_unsafe(ship1)
            ship1.path.pop()
            new_move = move
        # wait to leave for friendly, ... but make sure our old cell is available. prob should never happen
        # since we don't spawn with a ship already in shipyard, but rapid departure could cause this
        elif game.game_map[ship1].is_occupied:
            new_move = None # None == unwind
        else:
            ship_cell.mark_unsafe(ship1)
            new_move = 'o'

        if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} collision with ship {} while departing base {}. move {}".format(ship1.id, ship2.id, position, move))
    else:
        lateral_moves = [Direction.convert(m) for m in Direction.laterals(move)] + ["o"]
        new_move = resolve_random_move(game, collision, {"moves": lateral_moves})
        if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} collision at {} with ship {}. Resolving laterally {}, move {}".format(ship1.id, position, ship2.id , lateral_moves, move))

        # popping the path point will allow nav around the blocking ship, but this can
        # cause conjestion/screw up arrival/departure lanes when close to the base
        if new_move and len(ship1.path) > 1:
            new_position = get_position_from_move(game, ship1, new_move)
            d_next = game.game_map.calculate_distance(new_position, ship1.path[-1])
            d_plus_one = game.game_map.calculate_distance(new_position, ship1.path[-2])
            if d_next > d_plus_one:
                if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} next nav {} is farther than plus one {}. Popping next.".format(ship1.id, ship1.path[-1], ship1.path[-2]))
                ship1.path.pop()

    if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} - nav move collision resolved to {}".format(ship1.id, new_move))

    return new_move

def unwind(game, displaced_ship, ship_states):
    """
    Unwinds the moves starting from displaced_ship original position, would be better to consider unwinding
    all ships in cardinal positions based on priority/halite

    :param game
    :param displaced_ship Ship that no longer has a position. Offending ship took the position.
    :returns Returns the number of moves reverted
    """

    cell = game.game_map[displaced_ship]

    if DEBUG & (DEBUG_NAV): logging.info("Nav  - unwinding {}".format(cell.position))

    # the cell the ship moved from is still unoccupied
    if cell.ship is None:
        cell.ship = displaced_ship
        game.command_queue[displaced_ship.id] = displaced_ship.move(Direction.Still)
        return 1

    if DEBUG & (DEBUG_NAV): logging.info("Nav  - Ship {} is displaced from {} by ship {}".format(displaced_ship.id, displaced_ship.position, cell.ship.id))

    offending_ship = cell.ship # save the offending ship

    if offending_ship.status == "transiting":
        offending_ship.path.append(cell.position)

    cell.mark_unsafe(displaced_ship) # give the displace ship it's cell back

    game.command_queue[offending_ship.id] = offending_ship.move(Direction.Still)

    return unwind(game, offending_ship, ship_states) + 1

def ship_states_to_string(states):
    """
    Dump the ship states row by row so they're easier to read
    """
    out = []
    for k, v in states.items():
        out.append("Ship {}: {}".format(k, v))

    return "\n".join(out)

def get_base_surrounding_cardinals(game, position = None):
    """
    Given a position, get the closest base and surrounding cell positions

    :param game
    :param position
    :return Returns a list of positions
    """
    retval = []
    base = get_base_positions(game, position)
    for p in base.get_surrounding_cardinals():
        retval.append(p)

    return retval

def list_to_short_string(l, n):
    if n < len(l)/2:
        return "{} ... {}".format(str(l[:n])[:-1], str(l[-n:])[1:])
    else:
        return "{}".format(l)

def respond_to_sos(game, sos_call):
    """
    pop event
    find all close ships to sos event
    eval the chance of reaching the event loc
    send ship based on capacity


    sos -> (s_id, halite, position)
    """
    sos_position = sos_call["position"]
    sos_ship_id = sos_call["s_id"]
    sos_halite_lost = game.game_map[sos_position].halite_amount

    if DEBUG & (DEBUG_GAME): logging.info("Game - Sos recieved from ship {} @ {}. There was {} halite lost.".format(sos_ship_id, sos_position, sos_halite_lost))

    if sos_halite_lost < 300:
        if DEBUG & (DEBUG_GAME): logging.info("Game - Sos disregarded from ship {} @ {}. Halite lost is {}, threshold is {}".format(sos_ship_id, sos_position, sos_halite_lost, 500))
        return False

    block_size = 12
    block = CellBlock(game.game_map, Position(round(sos_position.x - block_size/2), round(sos_position.y - block_size/2)), block_size, block_size)

    cells = block.get_cells()

    enemies = []
    friendlies = []

    for cell in cells:
        if cell.is_occupied:
            distance = game.game_map.calculate_distance(cell.position, sos_position)
            if cell.ship.owner == game.me.id:
                if cell.ship.status != "returning" and cell.ship.status != "homing":
                    friendlies.append((cell.ship, distance))
            else:
                enemies.append((cell.ship, distance))

    friendlies.sort(key=lambda item: (item[1], item[0].halite_amount))
    enemies.sort(key=lambda item: (item[1]), reverse=True)

    # reward/risk
    # halite / ((f_best_dist * c1) + (e_cnt/f_cnt * c2) + (bf_dst/be_dst * c3)) c1,c2,c3 = .5,2,4 ???

    if enemies:
        best_enemy = enemies[-1]
        best_enemy_ship = best_enemy[0]
        best_enemy_distance = best_enemy[1]

    responder = False

    for friendly_ship, friendly_distance in friendlies:
        if enemies:
            if friendly_ship.halite_amount < 500 and friendly_distance < best_enemy_distance:
                responder = friendly_ship
                responder.path.append(sos_position)
                break
        else:
            if friendly_ship.halite_amount < 900:
                responder = friendly_ship
                responder.path.append(sos_position)
                break

    if DEBUG & (DEBUG_GAME):
        if friendlies:
           logging.info("Game - There are {} friendlies within {} moves of {}. The closest is ship {} @ {} away.".format(len(friendlies), block_size, sos_position, friendly_ship.id, friendly_distance))
        else:
            logging.info("Game - There are no friendlies within {} moves of {} with {} cargo capacity".format(block_size, sos_position, 600))

        if enemies:
           logging.info("Game - There are {} enemies within {} moves of {}. The closest is ship {} @ {} away.".format(len(enemies), block_size, sos_position, best_enemy_ship.id, best_enemy_distance))
        else:
            logging.info("Game - There are no enemies within {} moves of {}".format(block_size, sos_position))

        if responder and responder.assignments:
            if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} diverted from assignment {} to respond to sos from ship {} @ {}. t{}".format(responder.id, responder.assignments[-1], sos_ship_id, sos_position, game.turn_number))
        elif responder:
            if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} assigned to respond to sos from ship {} @ {}. t{}".format(responder.id, sos_ship_id, sos_position, game.turn_number))
        else:
            if DEBUG & (DEBUG_GAME): logging.info("Game - There are no viable ships to respond to sos from ship {} @ {}".format(sos_ship_id, sos_position))

        #ToDo: add the sos position as an assignment so others don't respond. Need to wait until there can be mult tasks per point

    return responder

def get_position_from_move(game, ship, move):
    move_offset = DIRECTIONS[move]
    return game.game_map.normalize(ship.position + Position(move_offset[0], move_offset[1]))
