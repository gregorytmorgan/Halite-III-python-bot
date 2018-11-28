#!/usr/bin/env python3
# Python 3.6

import hlt

from hlt import constants

import logging
import datetime
import numpy as np

# mybot code
from myutils.utils import *
from myutils.constants import *

#
# game setup
#

""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()

ship_states = {}

botName = "MyBot.test-example"

tasked_ships = {}

loiter_assignments = {}

#np.set_printoptions(precision=1, linewidth=240, floatmode="fixed", suppress=True)

#
# Coord map
#
#coord_map = game.game_map.get_coord_map()

#np.set_printoptions(threshold=1) # np.inf
#logging.debug("Coordinate Map {} {}".format(coord_map.shape, coord_map.dtype))
#logging.debug("\n{}".format(coord_map))

t_start = time.time()

#
# halite map
#
#halite_map = game.game_map.get_halite_map()

#np.set_printoptions(threshold=np.inf) # np.inf
#logging.debug("Halite Map {} {} Avg. halite: {}".format(halite_map.shape, halite_map.dtype, halite_map.mean()))
#logging.debug("\n{}".format(halite_map.astype(np.int64)))
#logging.debug("halite map - elapsed time: {}".format(time.time() - t_start))

#
# distance map
#
#distance_map = game.game_map.get_distance_map(game.me.shipyard.position)
#np.set_printoptions(threshold=np.inf) # np.inf
#logging.debug("Distance Map {} {}".format(distance_map.shape, distance_map.dtype))
#logging.debug("\n{}".format(distance_map.astype(np.int64)))
#logging.debug("distance map - elapsed time: {}".format(time.time() - t_start))

#
#  value map
#

cell_value_map = game.game_map.get_cell_value_map(game.me.shipyard.position)

#np.set_printoptions(threshold=np.inf) # np.inf
#logging.debug("Cell Value Map {} {}".format(cell_value_map.shape, cell_value_map.dtype))
#logging.debug("\n{}".format(cell_value_map.astype(np.int64))) # std display
#logging.debug(np.array2string(cell_value_map.astype(np.int64), separator=",")) # for pasteing as data

logging.debug("cell value - elapsed time: {}".format(time.time() - t_start))

#
# game start
#

game.ready(botName)

if DEBUG & (DEBUG_GAME): logging.info("Game - Successfully created bot! My Player ID is {}. {}".format(game.my_id, "{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now())))

""" <<<Game Loop>>> """

while True:
    turn_start_time = time.time()

    game.update_frame()

    me = game.me
    game_map = game.game_map

    command_queue = []

    #
    #
    #

    threshold = game_map.get_cell_value_map(me.shipyard.position).max() * .75
    hottest_areas = np.ma.MaskedArray(cell_value_map, mask= [cell_value_map < threshold], fill_value = 0)

    row, col = hottest_areas.nonzero()

    #################### in later game esp. need to adjust mining threshold based on remaining halite

    hotspots = []
    for y, x in zip(row, col):
        p = Position(x, y)
        hotspots.append((p, game_map[p].halite_amount))

    logging.debug("Pre-Hotspots: {}".format(hotspots))

    # remove the hotspots previosly assigned, but not reached
    hotspots[:] = [x for x in hotspots if x[0] not in loiter_assignments]

    logging.debug("Post-Hotspots: {}".format(hotspots))

    # sorted_blocks = sorted(moves, key=lambda item: item[2], reverse=True)
    targets = sorted(hotspots, key=lambda item: item[1])

    logging.debug("Targets: {}".format(targets))

    logging.debug("Loiter assignments: {}".format(loiter_assignments))

    for p_id, player in game.players.items():
        if p_id != me.id:
            enemy_base = player.shipyard.position
            break

    my_ships = me.get_ships()

    # initialize the ship states
    for ship in my_ships:
        if not (ship.id in ship_states):
            if DEBUG & (DEBUG_GAME): logging.info("Game - New ship with ID {}".format(ship.id))
            me.ship_count += 1
            ship_states[ship.id] = {
                "last_seen": game.turn_number,
                "prior_position": None,
                "prior_halite_amount": None,
                "status": "returning",
                "last_dock": game.turn_number,
                "christening": game.turn_number,
                "path": []
            }

            game.ship_christenings[ship.id] = game.turn_number

#            if len(tasked_ships) < 1:
#                logging.info("GAME - Ship {} is tasked".format(ship.id))
#                ship_states[ship.id]["status"] = "attacking"
#                tasked_ships[ship.id] = {
#                    "task_id": 1,
#                    "task_name": "cover_dropoff"
#                }

        # attribs not dependent on save state
        ship.last_seen = game.turn_number

        # update the current ship based on saved state
        ship.status = ship_states[ship.id]["status"]
        ship.path = ship_states[ship.id]["path"]
        ship.christening = ship_states[ship.id]["christening"]
        ship.last_dock = ship_states[ship.id]["last_dock"]

    # handle each ship for this turn
    for ship in my_ships:
        logging.info("Game - Ship {} at {} has {} halite and is {}".format(ship.id, ship.position, ship.halite_amount, ship.status))

        if ship.id in tasked_ships:
            if ship.position == enemy_base:
                logging.info("GAME - Ship {} arrived {}".format(ship.id, enemy_base))
                move = "o"
            else:
                #logging.info("GAME - Ship {} yard: {} enemy_base: {}".format(ship.id, me.shipyard.position, enemy_base))
                move = game_map.naive_navigate(ship, enemy_base)
        else:
            logging.info("GAME - Ship {} has a path of {} moves".format(ship.id, len(ship.path)))

            # logic for untasked ships
            if ship.status == "returning":
                if ship.position == me.shipyard.position:
                    ship.status = "exploring"
                    ship.path.clear()

                    # give the ship a destination off the target list
                    if len(targets) != 0:
                        loiter_point = targets.pop()[0]
                        loiter_assignments[loiter_point] = ship.id
                        logging.info("GAME - Ship {} assigned loiter {} off target list. {} targets remain".format(ship.id, loiter_point, len(targets)))
                        ship.path, cost = game_map.navigate(ship.position, loiter_point, "astar", {"move_cost": "turns"}) # heading out to loiter point
                    else:
                        logging.info("GAME - Ship {} No targets".format(ship.id))

                    # if a ship still doesn't have a path, just make a random move
                    if len(ship.path) == 0:
                        move = get_move(game, ship, "density")
                        logging.info("GAME - Ship {} is making a density move {}".format(ship.id, move))
                    else:
                        move = get_nav_move(game, ship, "astar", {"move_cost": "turns"})
                        logging.info("GAME - Ship {} is making a nav move {}".format(ship.id, move))
                else:
                    move = game_map.naive_navigate(ship, me.shipyard.position)
                    logging.info("GAME - Ship {} is heading home {}".format(ship.id, move))

            elif ship.halite_amount >= constants.MAX_HALITE:
                ship.status = "returning"
                move = game_map.naive_navigate(ship, me.shipyard.position)
                logging.info("GAME - Ship {} is heading home {}".format(ship.id, move))
            else:
                if len(ship.path) == 0:
                    move = get_move(game, ship, "density")
                    logging.info("GAME - Ship {} is making a density move {} at {}".format(ship.id, move, ship.position))
                    loiter_assignments.pop(ship.position, None)
                else:
                    move = get_nav_move(game, ship, "astar", {"move_cost": "turns"})
                    logging.info("GAME - Ship {} is making a nav move {}".format(ship.id, move))

        # move
        if check_fuel_cost(game, ship) and (game_map[ship.position].halite_amount < constants.MAX_HALITE / 10 or ship.is_full):
            logging.info("GAME - Ship {} is moving {}".format(ship.id, move))
            command_queue.append(ship.move(move))
        else:
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

    # check for lost ships
    lost_ship_ids = []
    for s_id in ship_states:
        if not me.has_ship(s_id):
            lost_ship_ids.append(s_id)
            logging.info("Game - Ship {} lost. Last seen on turn {}".format(s_id, ship_states[s_id]["last_seen"]))

    for s_id in lost_ship_ids:
        tasked_ships.pop(s_id, None)
        ship_states.pop(s_id, None)

    # check if we can spawn a ship
    if ships_are_spawnable(game):
        command_queue.append(me.shipyard.spawn())

    if DEBUG & (DEBUG_SHIP_STATES): logging.info("Game - end ship_states: {}".format(ship_states))

    if DEBUG: logging.info("Game - Turn time: {}".format(round(time.time() - turn_start_time, 4)))

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)


