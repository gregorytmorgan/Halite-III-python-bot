#
# Mybot code
#

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Position

import random
import logging

# mybot utils
from myutils.constants import *

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
    #loiterMult = loiterMult / maxArcTan * MaxLoiterDist

    #
    # linear
    #
    loiterMult = float((game.turn_number - 1) / constants.MAX_TURNS) * get_max_loiter_distance(game)

    # make sure we don't a useless mult
    if loiterMult < min_loiter_distance:
        loiterMult = min_loiter_distance

    return loiterMult

#
#
#
def get_dense_move(game, ship):
    moves = []
    for d in ship.position.get_surrounding_cardinals():
        if game.game_map[d].halite_amount > constants.MAX_HALITE/10 and not ship.is_full:
            moves.append((d.x, d.y, game.game_map[d].halite_amount))

    sorted_moves = sorted(moves, key=lambda item: item[2], reverse=True)

    logging.info("Ship - get_dense_move() - sorted_moves {}".format(sorted_moves))

    if len(sorted_moves) == 0:
        move = get_random_move(game, ship)
    else:
        pos = Position(sorted_moves[0][0] - ship.position.x, sorted_moves[0][1] - ship.position.y)
        logging.info("Ship - ship {} get_dense_move() - pos {}".format(ship.id, pos))

        moveOffset = game.game_map.normalize(pos)
        logging.info("Ship - ship {} get_dense_move() - moveOffset {}".format(ship.id, moveOffset))

        move = Direction.convert(game.game_map.naive_navigate(ship, ship.position + moveOffset))
        logging.info("Ship - ship {} get_dense_move() - move {}".format(ship.id, move))

        if move == "o":
            for i in range(1, len(sorted_moves)):
                moveOffset = game.game_map.normalize(Position(sorted_moves[i][0] - ship.position.x, sorted_moves[i][1] - ship.position.y))

                logging.info("Ship - ship {} get_dense_move() - moveOffset {}".format(ship.id, moveOffset))

                move = Direction.convert(game.game_map.naive_navigate(ship, moveOffset))
                if move != "o":
                    break

    if move == "o":
        logging.info("Ship - ship {} get_dense_move() - noop".format(ship.id))

    return move

#
#
#
def get_max_loiter_distance(game):
    if game.players == 2:
        max_loiter_distance = min(game.game_map.width / 2, MAX_LOITER)
    else:
        max_loiter_distance = min(game.game_map.height / 4, MAX_LOITER)

    return max_loiter_distance

#
#
#
def get_min_loiter_distance(game):
    # when a ship is sent off from the shipyard, this is the max distance.  It set
    # dynamically. The min loiter distance is stored as an offset, see min_loiter_distance
    return MIN_LOITER

#
#
#
def get_random_move(game, ship):

    moveChoice = random.choice(["n", "s", "e", "w"])
    #logging.info("Ship - get_random_move() - ship {} moveChoice2: {}".format(ship.id, moveChoice))

    moveOffset = ship.position.directional_offset(DIRECTIONS[moveChoice])
    #logging.info("Ship - get_random_move() - ship {} moveOffset2: {}".format(ship.id, moveOffset))

    move = Direction.convert(game.game_map.naive_navigate(ship, moveOffset))
    #logging.info("Ship - get_random_move() - ship {} final move2: {}".format(ship.id, move))

    if move == "o":
        original_move = move
        for i in range(4):
            # get char direction vs alt code below so we can log consistent msg
            # alt code: ship.move(random.choice([Direction.North, Direction.South, Direction.East, Direction.West]))
            moveChoice = random.choice(["n", "s", "e", "w"])
            moveOffset = ship.position.directional_offset(DIRECTIONS[moveChoice])
            move = Direction.convert(game.game_map.naive_navigate(ship, moveOffset))
            if move != "o":
                break

        if move == "o":
            logging.info("Ship - get_random_move() - ship {} Collision, original {}, correct failed".format(ship.id, original_move))
        else:
            logging.info("Ship - get_random_move() -  ship {} Collision, original {}, corrected {}".format(ship.id, original_move, move))

    return move

#
#
#
def spawn_ship(game):
    nShips = len(game.me.get_ships())

    if game.turn_number <= 100:
        maxShips = 8
    elif game.turn_number <= 200:
        maxShips = 6
    elif game.turn_number <= 300:
        maxShips = 4
    else:
        maxShips = 2

    if nShips >= maxShips:
        return False

    if game.me.halite_amount < constants.SHIP_COST:
        return False

    if game.game_map[game.me.shipyard].is_occupied:
        return False

    entryExitCells = game.me.shipyard.position.get_surrounding_cardinals()

    occupiedCells = 0
    for pos in entryExitCells:
        if game.game_map[pos].is_occupied:
            occupiedCells = occupiedCells + 1

    if occupiedCells > 0:
        return False

    return True

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
    mult = random.randint(1, round(len(game.me.get_ships()) / 2))

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

    logging.info("Ship - get_backoff_point() - ship {} backoffPoint {}".format(ship.id, backoffPoint))

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