#!/usr/bin/env python3
# Python 3.6

import hlt

from hlt import constants

import logging
import datetime

# mybot code
from myutils.utils import *
from myutils.constants import *

#
# main
#

""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()

ship_states = {}

botName = "MyBot.cover-dropoff"

tasked_ships = {}

#
# game start
#

game.ready(botName)

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
# Here, you log here your id, which you can always fetch from the game object by using my_id.
if DEBUG & (DEBUG_GAME): logging.info("Game - Successfully created bot! My Player ID is {}. {}".format(game.my_id, "{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now())))

""" <<<Game Loop>>> """

while True:
    game.update_frame()

    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    command_queue = []

    enemy_base = Position(8, 16)

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

            if len(tasked_ships) < 1:
                logging.info("GAME - Ship {} is tasked".format(ship.id))
                ship_states[ship.id]["status"] = "tasked"
                tasked_ships[ship.id] = {
                    "task_id": 1,
                    "task_name": "cover_dropoff"
                }

        # attribs not dependent on save state
        ship.last_seen = game.turn_number

        # update the current ship based on saved state
        ship.status = ship_states[ship.id]["status"]
        ship.path = ship_states[ship.id]["path"]
        ship.christening = ship_states[ship.id]["christening"]
        ship.last_dock = ship_states[ship.id]["last_dock"]

    # handle each ship for this turn
    for ship in my_ships:
        logging.debug("tasked_ships: {}".format(tasked_ships))

        logging.info("Game - Ship {} at {} has {} halite and is {}".format(ship.id, ship.position, ship.halite_amount, ship.status))

        if ship.id in tasked_ships:
            if ship.position == enemy_base:
                logging.info("GAME - Ship {} arrived {}".format(ship.id, enemy_base))
                move = "o"
            else:
                #logging.info("GAME - Ship {} yard: {} enemy_base: {}".format(ship.id, me.shipyard.position, enemy_base))
                move = game_map.naive_navigate(ship, enemy_base)
        else:
            # logic for untasked ships
            if ship.status == "returning":
                if ship.position == me.shipyard.position:
                    ship.status = "exploring"
                    move = random.choice([Direction.North, Direction.South, Direction.East, Direction.West])
                else:
                    move = game_map.naive_navigate(ship, me.shipyard.position)

            elif ship.halite_amount >= constants.MAX_HALITE / 4:
                ship.status = "returning"
                move = game_map.naive_navigate(ship, me.shipyard.position)
            else:
                move = random.choice([Direction.North, Direction.South, Direction.East, Direction.West])

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

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)


