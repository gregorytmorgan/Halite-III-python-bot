#!/usr/bin/env python3
# Python 3.6

import hlt

from hlt import constants

import logging
import datetime

from hlt.entity import Ship
from myutils.utils import *
from myutils.constants import *

#
# main
#

""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()

ship_states = {}

botName = "MyBot.cover-dropoff2"

def get_enemy_base():
    for p_id in player_ids:
        if p_id != me.id:
            enemy_base_position = game.players[p_id].shipyard.position
            break;
    return enemy_base_position

def cover_action1(ship):
    if not ship.path:
        logging.debug("action not path".format())
        ship.path, cost = game_map.navigate(ship.position, get_enemy_base(), "astar", {"move_cost": "turns"})
    else:
        logging.debug("action path".format())

    logging.debug("path: {}".format(ship.path))

def cover_move1(ship):
    if not ship.path:
        logging.debug("move not path".format())
        move = "o"
    else:
        logging.debug("move path".format())
        args = {"waypoint_algorithm": "astar", "move_cost": "turns"}
        move = get_move(game, ship, "nav", args) # path scheme = algo for incomplete path

    return move

def cover_action2(ship):
    pass

def cover_move2(ship):
    pass

def assign_task(task, ship):
    logging.info("GAME - Ship {} is tasked with '{}'".format(ship.id, task["task_name"]))
    ship_states[ship.id]["status"] = "tasked"
    task["ships"].append(ship.id)

def abort_task(task, ship_id = None):
    if ship_id is None:
        for sid in task["ships"]:
            if sid in me.get_ships():
                me.get_ship(sid).status = "exploring"
            task["ships"].remove(sid)
            logging.info("GAME - Ship {} is aborting task '{}'".format(ship.id, task["task_name"]))
    else:
        if ship_id in me.get_ships():
            me.get_ship(ship_id).status = "exploring"
        if ship_id in task["ships"]:
            task["ships"].remove(ship_id)

    logging.info("GAME - Ship {} is aborting task '{}'".format(ship_id, task["task_name"]))

def get_task(target):
    if isinstance(target, str):
        for tid, t in tasks.items():
            if t["task_name"] == target:
                return t
        return None
    elif isinstance(target, Ship):
        for tid, t in tasks.items():
            if target.id in t["ships"]:
                return t
        return None
    elif isinstance(target, int):
        if target in tasks:
            return tasks[target]
        return None
    else:
        raise RuntimeError("Invalid target: ".format(target))

tasks = {
    1: {
        "task_id": 1,
        "task_name": "cover_dropoff",
        "action": cover_action1,
        "move": cover_move1,
        "ships": [],
        "active": True,
        "ships_required": 1
    },
    2: {
        "task_id": 2,
        "task_name": "cover_dropoff2",
        "action": cover_action2,
        "move": cover_move2,
        "ships": [],
        "active": False
    },
}

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

    player_ids = list(game.players.keys())

    random.shuffle(player_ids)

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

            # assign tasks
            for t_id, task in tasks.items():
                if not task["active"]:
                    logging.debug("{} is not active".format(task["task_name"]))
                    continue

                logging.debug("{} is active".format(task["task_name"]))

                xt = get_task(ship)
                logging.debug("s:{}, req: {}, xt: {}".format(len(task["ships"]), task["ships_required"], xt))

                if len(task["ships"]) < task["ships_required"] and not get_task(ship):
                    assign_task(task, ship)

        # attribs not dependent on save state
        ship.last_seen = game.turn_number

        # update the current ship based on saved state
        ship.status = ship_states[ship.id]["status"]
        ship.path = ship_states[ship.id]["path"]
        ship.christening = ship_states[ship.id]["christening"]
        ship.last_dock = ship_states[ship.id]["last_dock"]

    # handle each ship for this turn
    for ship in my_ships:
        logging.debug("tasks: {}".format(tasks))

        logging.info("Game - Ship {} at {} has {} halite and is {}".format(ship.id, ship.position, ship.halite_amount, ship.status))

        task = get_task(ship)

        logging.debug("ship task: {}".format(task))

        if task:
            task["action"](ship)
        else:
            # logic for untasked ships
            if ship.status == "returning":
                if ship.position == me.shipyard.position:
                    ship.status = "exploring"
                    move = get_move(game, ship, "random", "random")
                else:
                    move = game_map.naive_navigate(ship, me.shipyard.position)

            elif ship.halite_amount >= constants.MAX_HALITE / 4:
                ship.status = "returning"
                move = game_map.naive_navigate(ship, me.shipyard.position)
            else:
                move = get_move(game, ship, "random", "random")

        # move
        if task:
            move = task["move"](ship)
            move = "o" if move is None else move
            move_cmd = ship.move(move)
        elif fuel_ok(game, ship) and move_ok(game, ship) and move is not None:
            move_cmd = ship.move(move)
        else:
            move_cmd = ship.stay_still()

        command_queue.append(move_cmd)

        logging.info("GAME - Ship {} is moving {}".format(ship.id, move))

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
        task = get_task(s_id)
        if task:
            abort_task(task, s_id)
        ship_states.pop(s_id, None)

    # check if we can spawn a ship
    if spawn_ok(game):
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)


