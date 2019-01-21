#
#
#

import random
import logging

from operator import itemgetter

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
        ship.path, cost = game.game_map.navigate(ship.position, Position(x,y), "astar", {"move_cost_type": "turns", "excludes":bases})
    else:
        logging.debug("Task - Ship {} is moving to random point {}".format(ship.id, ship.path[0]))

    next_move = get_move(game, ship, "nav", {"waypoint_algorithm": "astar", "move_cost_type": "turns"})
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
            ship.path, cost = game.game_map.navigate(ship.position, dropoff_position, "astar", {"move_cost_type": "turns", "excludes": get_base_positions(game)})

        if ship.position == dropoff_position:
            if game.me.halite_amount >= 4000:
                logging.debug("Task - Ship {} at dropoff deploy point {}. Deploying.".format(ship.id, dropoff_position))
                game.command_queue[ship.id] = ship.make_dropoff()
                game.me.halite_amount -= 4000
                game.fund_dropoff -= 1
                return (dropoff_position)
            else:
                logging.debug("Task - Ship {} at dropoff deploy point {}. Insufficient halite ({}).".format(ship.id, dropoff_position, game.me.halite_amount))
                game.command_queue[ship.id] = ship.move('o')
                game.fund_dropoff += 1
        else:
            next_move = get_move(game, ship, "nav", {"waypoint_algorithm": "astar", "move_cost_type": "turns"})
            if next_move:
                game.command_queue[ship.id] = ship.move(next_move)

        return False

    return action


def dropoff_complete(game, ship, dropoff_position):
    logging.debug("Task - Ship {} completed deploy_dropoff".format(ship.id))

    ship_candidates = []

    my_ships = game.me.get_ships()

    base_positions = get_base_positions(game)

    closest_base_position = False
    for base_position in base_positions:
        distance = game.game_map.calculate_distance(base_position, dropoff_position)
        if closest_base_position is False or closest_base_distance > distance:
            closest_base_position = base_position
            closest_base_distance = distance

    for s in my_ships:
        distance = game.game_map.calculate_distance(s.position, dropoff_position)
        if s.status == "transiting" or ship.status == "exploring":
            ship_candidates.append((s, distance))

    #
    # Disabled until there is a way to decide how many ships to send.  Sending too
    # many can cause problems
    #
    if False and ship_candidates:
        ship_candidates.sort(key=itemgetter(1), reverse=True)
        ship_count = 0
        for candidate in ship_candidates:
            s = candidate[0]
            s_distance = candidate[1]

            s.path.clear()

            s.status = "tasked"
            s.tasks.append(make_goto_task(dropoff_position, -4))

            # use the std nav instead of goto_task if ship should mine on the way to new dropoff
            #s.path, cost = game.game_map.navigate(s.position, dropoff_position, "astar", {"move_cost_type": "turns"})

            logging.debug("Tasking ship {} to dropoff {}".format(s.id, dropoff_position))

            if ship_count > 4:
                break

            if s_distance > closest_base_distance/2 or s_distance < 5:
                continue

            ship_count += 1

    return True

def make_dropoff_task(dropoff_position):
    return Task("deploy_dropoff_" + str(dropoff_position), make_dropoff_action(dropoff_position), dropoff_complete)

#t_deploy_dropoff = Task("deploy_dropoff", make_dropoff_action(dropoff_position), dropoff_complete)


#
# Goto a point (fast, no mining)
#

def make_goto_action(p, modifier = 0):
    """
    Go to position p

    :param dropoff_position
    :param modifer How much of the end of the path to drop ... this works as a 'get close to'
    """
    def action(game, ship):

        if not ship.path and ship.position != p:
            path, cost = game.game_map.navigate(ship.position, p, "astar", {"move_cost_type": "turns"})

            #if modifier:
            #    path = path[:-modifier]

            if path is None:
                logging.warn("Navigate failed (returned None). Use ship path of current position.")
                ship.path.append(ship.position)
            else:
                ship.path = path

        if ship.position == p:
            #ship.status = "returning"
            return True
        else:
            next_move = get_move(game, ship, "nav", {"waypoint_algorithm": "astar", "move_cost_type": "turns"})
            if next_move:
                game.command_queue[ship.id] = ship.move(next_move)

        return False

    return action

def goto_complete(game, ship, retval):
    logging.debug("Task - Ship {} completed goto task {}".format(ship.id, ship.position))
    return True

def make_goto_task(p, modifier):
    return Task("goto_" + str(p), make_goto_action(p, modifier), goto_complete)

