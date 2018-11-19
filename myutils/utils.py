#
# Mybot code
#

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Position

import os
import time
import math
import random
import logging
import numpy as np

# mybot utils
from myutils.constants import *

#
#
#
def get_mining_rate(game):
    mined = []

    if len(game.game_metrics["mined"]) == 0:
        return 0

    trailing_turn = 1 if game.turn_number < 50 else 50
    i = len(game.game_metrics["mined"]) - 1
    while i >= 0 and game.game_metrics["mined"][i][0] > trailing_turn:
        mined.append(game.game_metrics["mined"][i][2])
        i -= 1

    return np.average(mined)


#
#
#
def ships_are_spawnable(game):
    safety_margin = 2.0
    ship_cost = constants.SHIP_COST
    ship_count = len(game.me.get_ships())

    if ship_count >= MAX_SHIPS:
        return False

    if ship_count == 0:
        return True

    mining_rate = get_mining_rate(game) / ship_count

    if mining_rate == 0:
        return True

    payback = ship_cost / mining_rate

    remaining_turns = constants.MAX_TURNS - game.turn_number

    return (payback * safety_margin) < remaining_turns


#
#
#
def spawn_ship(game):

    if not ships_are_spawnable(game):
        return False

    if game.me.halite_amount < constants.SHIP_COST:
        return False

    if game.game_map[game.me.shipyard].is_occupied:
        return False

    entryexit_cells = game.me.shipyard.position.get_surrounding_cardinals()

    occupied_cells = 0
    for pos in entryexit_cells:
        if game.game_map[pos].is_occupied:
            occupied_cells = occupied_cells + 1

    if occupied_cells > 0:
        return False

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
# nav moves resolv first by density, then randomly
#
def get_density_move(game, ship):

    move = "o"

    if DEBUG & (DEBUG_NAV): logging.info("Nav - ship {} is getting a density based move".format(ship.id))

    if not check_fuel_cost(game, ship):
        return move

    moves = []
    for d in ship.position.get_surrounding_cardinals():
        if game.game_map[d].halite_amount > constants.MAX_HALITE/10:
            moves.append((d.x, d.y, game.game_map[d].halite_amount))

    sorted_moves = sorted(moves, key=lambda item: item[2], reverse=True)

    if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} sorted_moves: {}".format(ship.id, sorted_moves))

    if len(sorted_moves) != 0:
        for i in range(0, len(sorted_moves)):
            move_offset = (sorted_moves[i][0] - ship.position.x, sorted_moves[i][1] - ship.position.y)
            if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} moveOffset: {}".format(ship.id, move_offset))

            new_position = game.game_map.normalize(Position(sorted_moves[i][0], sorted_moves[i][1]))
            if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} new_position: {}".format(ship.id, new_position))

            normalized_position = game.game_map.normalize(new_position)
            if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} normalized_position: {}".format(ship.id, normalized_position))

            cell = game.game_map[normalized_position]

            if not cell.is_occupied:
                move = Direction.convert(move_offset)
                cell.mark_unsafe(ship)
                break

    # if we were not able to find a usable dense cell, try to find a random one
    if move == "o":
        if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} Collision, trying to find a random move".format(ship.id))
        move = get_random_move(game, ship)

    if move == "o":
        if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} Collision, unable to find a move".format(ship.id))

    return move

#
# nav moves resolv randomly
#
def get_random_move(game, ship):

    move = "o"

    if DEBUG & (DEBUG_NAV): logging.info("NAV - ship {} getting random move".format(ship.id))

    if not check_fuel_cost(game, ship):
        return move

    moves = ["n", "s", "e", "w"]

    moveIdx = random.randint(0, 3)

    for idx in range(moveIdx, moveIdx + 4):
        moveChoice = moves[idx % 4]
        if DEBUG & (DEBUG_NAV): logging.info("NAV - get_random_move() - ship {} moveChoice2: {} {}".format(ship.id, idx, moveChoice))

        new_position = ship.position.directional_offset(DIRECTIONS[moveChoice])
        if DEBUG & (DEBUG_NAV): logging.info("NAV - get_random_move() - ship {} new_position: {}".format(ship.id, new_position))

        normalized_position = game.game_map.normalize(new_position)
        if DEBUG & (DEBUG_NAV): logging.info("NAV - ship {} normalized_position {}".format(ship.id, normalized_position))

        cell = game.game_map[normalized_position]

        if not cell.is_occupied:
            cell.mark_unsafe(ship)
            move = moveChoice
            break

    return move

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

#
#
#
def get_dropoff_position(game, ship):
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
# nav moves resolv randomly
#
def get_ship_nav_move(game, ship, algo = "astar", args = {"move_cost": "turns"}):
    game_map = game.game_map

    if DEBUG & (DEBUG_NAV): logging.info("NAV - ship {} getting nav move for path {}".format(ship.id, ship.path))

    if not check_fuel_cost(game, ship):
        return 'o'

    if len(ship.path) == 0:
        if DEBUG & (DEBUG_NAV): logging.info("NAV - ship {} empty path".format(ship.id))
        return 'o'

    next_position = ship.path[len(ship.path) - 1]

     # check to see if we have a waypoint, not a continous path
    if game_map.calculate_distance(ship.position, next_position) > 1:
        normalized_next_position = game_map.normalize(next_position)

        if DEBUG & (DEBUG_NAV): logging.info("NAV - ship {} found waypoint {} ({}), calulating complete path".format(ship.id, next_position, normalized_next_position))

        # calc a continous path
        path, cost = game_map.navigate(ship, normalized_next_position, algo, args)

        if path == None:
            if DEBUG & (DEBUG_NAV): logging.info("NAV - ship {} Nav failed, can't reach {}".format(ship.id, normalized_next_position))
            return 'o'
        else:
            if DEBUG & (DEBUG_NAV): logging.info("NAV - ship {} path to waypoint found with a cost of {} ({} turns)".format(ship.id, cost, len(path)))
            ship.path.pop()
            ship.path = ship.path + path

    new_position = ship.path[len(ship.path) - 1]
    if DEBUG & (DEBUG_NAV): logging.info("NAV - ship {} new_position1 {}".format(ship.id, new_position))

    normalized_new_position = game_map.normalize(new_position)
    if DEBUG & (DEBUG_NAV): logging.info("NAV - ship {} normalized_new_position1 {}".format(ship.id, normalized_new_position))

    if normalized_new_position == ship.position:
        ship.path.pop()
        return 'o'

    cell = game_map[normalized_new_position]

    # once we have the move, handle collisions
    if cell.is_occupied:
        move = get_random_move(game, ship)
        if move == "o":
            if DEBUG & (DEBUG_NAV): logging.info("NAV - ship {} collision at {} with ship {}, using {}".format(ship.id, normalized_new_position, cell.ship.id , move))
    else:
        cell.mark_unsafe(ship)
        ship.path.pop()

        # use get_unsafe_moves() to get a normalized directional offset. We should always get one soln.
        offset = game_map.get_unsafe_moves(ship.position, normalized_new_position)[0]
        move = Direction.convert(offset)

    return move

#
#
#
def check_fuel_cost(game, ship):
    fuelCost = game.game_map[ship.position].halite_amount * .1

    if round(fuelCost) > ship.halite_amount:
        if DEBUG & (DEBUG_NAV): logging.info("NAV - Ship {} has insuffient fuel. Have {}, need {}".format(ship.id, ship.halite_amount, round(fuelCost, 2)))
        return False

    return True

#
#
#
def dump_stats(game, data, key = "all"):
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
        with open(stats_dir + '/' + k + "-" + ts + "-bot-" + str(game.me.id) + ".txt", "w") as f:
            for line in data[k]:
                f.write(str(line) + "\n")