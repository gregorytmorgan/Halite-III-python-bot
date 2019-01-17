#
#
#

import random
import logging

from hlt.positionals import Position

from myutils.utils import get_move, get_base_positions
from myutils.task import Task

#
# Example task
#
def random_path_action(game, ship):
    if not ship.path:
        x = random.randint(0, game.game_map.width - 1)
        y = random.randint(0, game.game_map.height - 1)
        logging.debug("Task - Ship {} is moving to a new random point {}".format(ship.id, Position(x,y)))
        bases = get_base_positions(game)
        ship.path, cost = game.game_map.navigate(ship.position, Position(x,y), "astar", {"move_cost": "turns", "excludes":bases})
    else:
        logging.debug("Task - Ship {} is moving to random point {}".format(ship.id, ship.path[0]))

    next_move = get_move(game, ship, "nav", {"waypoint_algorithm": "astar", "move_cost": "turns"})
    if next_move:
        game.command_queue[ship.id] = ship.move(next_move)

    if ship.is_full:
        return True
    else:
        return False

def random_path_complete(game, ship, retval):
    logging.debug("Task - Ship {} completed moving randomly".format(ship.id))
    return True

t_move_randomly = Task("move_randomly", random_path_action, random_path_complete)


#
# Deploy dropoff
#

def make_dropoff_action(dropoff_position):
    def action(game, ship):

        logging.debug("Task - Ship {} is deploying dropoff to {}".format(ship.id, dropoff_position))

        if not ship.path and ship.position != dropoff_position:
            ship.path, cost = game.game_map.navigate(ship.position, dropoff_position, "astar", {"move_cost": "turns", "excludes": get_base_positions(game)})

        if ship.position == dropoff_position:
            if game.me.halite_amount >= 4000:
                logging.debug("Task - Ship {} at dropoff deploy point {}. Deploying.".format(ship.id, dropoff_position))
                game.command_queue[ship.id] = ship.make_dropoff()
                game.me.halite_amount -= 4000
                game.fund_dropoff -= 1
                return True
            else:
                logging.debug("Task - Ship {} at dropoff deploy point {}. Insufficient halite ({}).".format(ship.id, dropoff_position, game.me.halite_amount))
                game.command_queue[ship.id] = ship.move('o')
                game.fund_dropoff += 1
        else:
            next_move = get_move(game, ship, "nav", {"waypoint_algorithm": "astar", "move_cost": "turns"})
            if next_move:
                game.command_queue[ship.id] = ship.move(next_move)

        return False

    return action


def dropoff_complete(game, ship, retval):
    logging.debug("Task - Ship {} completed deploy_dropoff".format(ship.id))
    return True

def make_dropoff_task(dropoff_position):
    return Task("deploy_dropoff", make_dropoff_action(dropoff_position), dropoff_complete)

#t_deploy_dropoff = Task("deploy_dropoff", make_dropoff_action(dropoff_position), dropoff_complete)
