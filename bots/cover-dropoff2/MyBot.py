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

#
#
#

def cover_shipyard_action(game, ship):
    if not ship.path:
        ship.path, cost = game_map.navigate(ship.position, get_enemy_base(), "astar", {"move_cost": "turns"})

def cover_cell_move(game, ship):
    if not ship.path or not fuel_ok(game, ship):
        move = "o"
    else:
        args = {"waypoint_algorithm": "astar", "move_cost": "turns"}
        move = get_move(game, ship, "nav", args) # path scheme = algo for incomplete path

    return move

def cover_dropoff_north_action(game, ship):
    target = get_enemy_base().directional_offset(Direction.North)
    target.y -= 4
    if not ship.path:
        ship.path, cost = game_map.navigate(ship.position, target, "astar", {"move_cost": "turns"})

def cover_dropoff_south_action(game, ship):
    target = get_enemy_base().directional_offset(Direction.South)
    #target.y += 4
    if not ship.path:
        ship.path, cost = game_map.navigate(ship.position, target, "astar", {"move_cost": "turns"})

def cover_dropoff_east_action(game, ship):
    target = get_enemy_base().directional_offset(Direction.East)
    if not ship.path:
        ship.path, cost = game_map.navigate(ship.position, target, "astar", {"move_cost": "turns"})

def cover_dropoff_west_action(game, ship):
    target = get_enemy_base().directional_offset(Direction.West)
    if not ship.path:
        ship.path, cost = game_map.navigate(ship.position, target, "astar", {"move_cost": "turns"})

#
#
#

def get_enemy_base():
    for p_id in player_ids:
        if p_id != me.id:
            enemy_base_position = game.players[p_id].shipyard.position
            break;
    return enemy_base_position

def assign_task(task, target_ship):
    if isinstance(target_ship, int):
        if me.has_ship(target_ship):
            ship = me.get_ship(target_ship)
    elif isinstance(target_ship, Ship):
        ship = target_ship
    else:
        raise RuntimeError("Invalid target_ship: ".format(target))

    logging.info("GAME - Ship {} is tasked with '{}'".format(ship.id, task["task_name"]))
    ship_states[ship.id]["status"] = "tasked"
    ship.status = "tasked"
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

def get_task_by_ship_id(s_id):
    for tid, t in tasks.items():
        if s_id in t["ships"]:
            return t
    return None

def get_task(target):
    if isinstance(target, str):
        for tid, t in tasks.items():
            if t["task_name"] == target:
                return t
        return None
    elif isinstance(target, Ship):
        return get_task_by_ship_id(target.id)
    elif isinstance(target, int):
        if target in tasks:
            return tasks[target]
        return None
    else:
        raise RuntimeError("Invalid target: ".format(target))

tasks = {
    1: {
        "id": 1,
        "task_name": "cover_shipyard",
        "action": cover_shipyard_action,
        "move": cover_cell_move,
        "ships": [],
        "active": False,
        "ships_required": 1
    },
    2: {
        "id": 2,
        "task_name": "cover_dropoff_north",
        "action": cover_dropoff_north_action,
        "move": cover_cell_move,
        "ships": [],
        "active": True,
        "ships_required": 1
    },
    3: {
        "id": 3,
        "task_name": "cover_dropoff_south",
        "action": cover_dropoff_south_action,
        "move": cover_cell_move,
        "ships": [],
        "active": True,
        "ships_required": 1
    },
    4: {
        "id": 4,
        "task_name": "cover_dropoff_east",
        "action": cover_dropoff_east_action,
        "move": cover_cell_move,
        "ships": [],
        "active": True,
        "ships_required": 1
    },
    5: {
        "id": 5,
        "task_name": "cover_dropoff_west",
        "action": cover_dropoff_west_action,
        "move": cover_cell_move,
        "ships": [],
        "active": True,
        "ships_required": 1
    }
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

    game.collisions.clear()
    game.command_queue.clear()

    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    player_ids = list(game.players.keys())

    random.shuffle(player_ids)

    my_ships = me.get_ships()

    #
    # initialize the ship states
    #
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

        # attribs not dependent on save state
        ship.last_seen = game.turn_number

        # update the current ship based on saved state
        ship.status = ship_states[ship.id]["status"]
        ship.path = ship_states[ship.id]["path"]
        ship.christening = ship_states[ship.id]["christening"]
        ship.last_dock = ship_states[ship.id]["last_dock"]

    #
    # assign tasks
    #

    at = None
    for t in tasks.values():
        if t["active"]:
            at = "Task {} has ships {}".format(t["id"], t["ships"])
    logging.debug("Active tasks: {}".format(at))

    tasked_ships = []
    for t in tasks.values():
        if t["ships"]:
            tasked_ships += t["ships"]

    untasked_ships = []
    for ship in my_ships:
        if ship.id not in tasked_ships:
            untasked_ships.append(ship.id)

    # assign tasks
    for t_id, task in tasks.items():
        if not task["active"]:
            logging.debug("{} is not active".format(task["task_name"]))
            continue

        logging.debug("{} is active".format(task["task_name"]))

        if len(task["ships"]) < task["ships_required"]:
            if len(untasked_ships) > 2: # leave a couple of ships around to mine
                s_id = untasked_ships.pop()
                logging.debug("Ship {} is assigned task '{}'".format(s_id, task["task_name"]))
                assign_task(task, s_id)
            else:
                logging.debug("Task {} needs {} move ships, but there are no untasked ships".format(task["task_name"], task["ships_required"] - len(task["ships"])))

    #
    # handle each ship for this turn
    #
    for ship in my_ships:

        logging.info("Game - Ship {} at {} has {} halite and is {}".format(ship.id, ship.position, ship.halite_amount, ship.status))

        # logic
        if ship.status == "tasked":
            task = get_task(ship)
            task["action"](game, ship)
        elif ship.status == "returning":
            if ship.position == me.shipyard.position:
                ship.status = "exploring"
        elif ship.status == "exploring":
            if ship.halite_amount >= constants.MAX_HALITE / 4:
                ship.status = "returning"
        else:
            raise RuntimeError("Unknown ship status: {}".format(ship.status))

        # move
        if ship.status == "tasked":
            move = task["move"](game, ship)
        elif ship.status == "returning":
            if fuel_ok(game, ship):
                move = game_map.naive_navigate(ship, me.shipyard.position)
        elif ship.status == "exploring":
            if move_ok(game, ship) and fuel_ok(game, ship):
                move = get_move(game, ship, "density", "random")
            else:
                move = "o"
        else:
            raise RuntimeError("Unknown ship status: {}".format(ship.status))

        logging.debug("move: {}".format(move))

        if not (move is None):
            game.command_queue[ship.id] = ship.move(move)

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
        logging.info("Game - Ship {} lost. pop state".format(s_id))
        ship_states.pop(s_id, None)
        task = get_task_by_ship_id(s_id)
        if task:
            logging.info("Game - Ship {} lost. abort task {}".format(s_id, task["id"]))
            abort_task(task, s_id)

    #
    # resolve collisions
    #
    resolve_collsions(game)

    # check if we can spawn a ship
    if spawn_ok(game):
        game.command_queue[-1] = me.shipyard.spawn()

    #logging.debug("game.command_queue: {}".format(game.command_queue))

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(list(game.command_queue.values()))
