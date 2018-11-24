#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt

# This library contains constant values.
from hlt import constants

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
# (print statements) are reserved for the engine-bot communication.
import logging
import datetime
import math
import time
import numpy as np

# mybot code
from myutils.utils import *
from myutils.constants import *

#
# main
#

""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()

# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.

# keep ship state inbetween turns
ship_states = {}

botName = "MyBot.v15"

#
# game start
#

game.ready(botName)

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
# Here, you log here your id, which you can always fetch from the game object by using my_id.
if DEBUG & (DEBUG_GAME): logging.info("Game - Successfully created bot! My Player ID is {}. {}".format(game.my_id, "{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now())))

""" <<<Game Loop>>> """

while True:
    turn_spent = 0
    turn_gathered = 0
    turn_start_time = time.time()

    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    # running update_frame().
    game.update_frame()

    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map
    game_metrics = game.game_metrics

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    # end of the turn.
    command_queue = []

    my_ships = me.get_ships()

    #
    # initialize the ship states
    #
    for ship in my_ships:
        if ship.id in ship_states:

            # we calc mined amount and fuel cost based on the diff of what we had
            # last turn and what the server says we have now
            if ship.halite_amount != ship_states[ship.id]["prior_halite_amount"]:
                if ship.halite_amount == 0:
                    fuel_cost = math.floor(game_map[ship_states[ship.id]["prior_position"]].halite_amount * .1)
                    gathered = ship_states[ship.id]["prior_halite_amount"] - fuel_cost
                    turn_gathered += gathered
                    game_metrics["gathered"].append((game.turn_number, ship.id, gathered))
                elif ship.halite_amount < ship_states[ship.id]["prior_halite_amount"]:
                    fuel_cost = ship_states[ship.id]["prior_halite_amount"] - ship.halite_amount
                    game_metrics["burned"].append((game.turn_number, ship.id, fuel_cost))
                else:
                    mined = ship.halite_amount - ship_states[ship.id]["prior_halite_amount"]
                    game_metrics["mined"].append((game.turn_number, ship.id, mined))

        else:
            if DEBUG & (DEBUG_GAME): logging.info("Game - New ship with ID {}".format(ship.id))
            me.ship_count += 1

            turn_spent = constants.SHIP_COST
            game_metrics["spent"].append((game.turn_number, turn_spent))

            ship_states[ship.id] = {
                "last_seen": game.turn_number,
                "prior_position": None,
                "prior_halite_amount": None,
                "status": "returning",
                "last_dock": game.turn_number,
                "christening": game.turn_number,
                "path": []
            }

            # we can't attach a christening attrib to the acutal ship obj because we'll lose
            # the info once the ship is destroyed. We're interested in destroyed ship info when
            # we calc stats such as mining rate
            game.ship_christenings[ship.id] = game.turn_number

        # attribs not dependent on save state
        ship.last_seen = game.turn_number

        # update the current ship based on saved state
        ship.status = ship_states[ship.id]["status"]
        ship.path = ship_states[ship.id]["path"]
        ship.christening = ship_states[ship.id]["christening"]
        ship.last_dock = ship_states[ship.id]["last_dock"]

        # note, some ship state attribs are not stored on the actual ship object:
        # prior_position, prior_halite_amount

    #
    # handle each ship for this turn
    #
    for ship in my_ships:
        dropoff_position = get_dropoff_position(game, ship)

        if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} at {} has {} halite and is {}".format(ship.id, ship.position, ship.halite_amount, ship.status))

        #
        # status - returning
        #
        if ship.status == "returning":
            #
            # Returning - in transit
            #
            if ship.position == dropoff_position:
                dropoff_amount = ship_states[ship.id]["prior_halite_amount"]
                if not (dropoff_amount is None):
                    if DEBUG & (DEBUG_GAME): logging.info("GAME - Ship {} completed dropoff of {} halite at {}. Return took {} turns".format(ship.id, dropoff_amount, dropoff_position, game.turn_number - ship.last_dock))

                #ship.path.clear()

                if me.ship_count <= 4:
                    cardinals = ["w", "n", "s", "e"]
                    hint = cardinals[me.ship_count % 4]
                    loiter_point = get_loiter_point(game, ship, hint)
                    departure_point = None
                else:
                    hint = None
                    loiter_point = get_loiter_point(game, ship, hint)
                    departure_point = get_departure_point(dropoff_position, loiter_point)

                if departure_point is None:
                    path, cost = game_map.navigate(dropoff_position, loiter_point, "astar", {"move_cost": "turns"}) # heading out to loiter point
                else:
                    path, cost = game_map.navigate(departure_point, loiter_point, "astar", {"move_cost": "turns"}) # heading out to loiter point
                    path.append(departure_point)

                if DEBUG & (DEBUG_NAV): logging.info("Nav - Ship {} has a departure point of {} for loiter point {}. Hint: {}".format(ship.id, departure_point, loiter_point, hint))

                if path is None:
                    if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} Error, navigate return None")
                    ship.path = []
                    logging.warning("Ship {} Error, navigate failed for loiter point {}".format(ship.id, loiter_point))
                else:
                    ship.path = path
                    if DEBUG & (DEBUG_NAV): logging.info("Ship - Ship {} is heading out to {}, ETA {} turns ({}).".format(ship.id, loiter_point, len(ship.path), round(cost)))

                ship.status = "exploring"
            else:
                #
                # Returning - in transit
                #

                # For a returning ship in transit, we don't need to do anything, the move
                # code will grab the next position/point and create a move for it
                if DEBUG & (DEBUG_NAV): logging.info("Ship - Ship {} is {} away from dropoff ({}). ETA {} turns.".format(ship.id, game_map.calculate_distance(ship.position, dropoff_position), dropoff_position, len(ship.path)))

        #
        # status - backing off
        #
        elif ship.status == "backingoff":

            # a ship is backing off when collides during return.  Backoff involves reversing direction
            # for a random number of moves toword a backoff point. Once the backoff point is reached, the
            # ship will return to a 'returning' status
            if len(ship.path) == 0:
                ship.status = "returning"
                ship.path.append(dropoff_position) # complet path will be calc'd by get_move if the distance to dropoff_position is > 1
                if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} backoff is complete to {}".format(ship.id, ship.position))
            else:
                if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} is backing off to {}".format(ship.id, ship.path[0]))

        #
        # status - ship full
        #
        elif ship.halite_amount >= constants.MAX_HALITE or ship.is_full:
            ship.status = "returning"

            if not (ship.halite_amount is None):
                game_metrics["return_duration"].append((game.turn_number, ship.id, game.turn_number - ship.last_dock))

            path, cost = game_map.navigate(ship.position, dropoff_position, "dock") # returning to shipyard/dropoff

            if path is None:
                if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} Error, navigate return None")
                ship.path = []
                logging.warning("Ship {} Error, navigate failed for dropoff {}".format(ship.id, dropoff_position))
            else:
                ship.path = path
                if DEBUG & (DEBUG_SHIP): logging.info("Ship - Ship {} is now returning to {} at a cost of {} ({} turns)".format(ship.id, dropoff_position, round(cost, 1), len(ship.path)))

        #
        # Move
        #

        # if cell is essentially empty then continue, if the ship is full continue
        # else we'll stay in place and mine
        if should_move(game, ship):
            #
            # exploring (not mining)
            #
            # if we're already at out next position, pop it off we don't waste the turn
            if len(ship.path) and ship.position == ship.path[len(ship.path) - 1]:
                logging.warning("Ship {} popped a useless point {}".format(ship.id, ship.path[len(ship.path) - 1]))
                ship.path.pop()

            if len(ship.path) == 0:
                move = get_move(game, ship, "density")
                if DEBUG & (DEBUG_GAME): logging.info("GAME - Ship {} is exploring to the {}".format(ship.id, move))
            else:
                # here, the path scheme specifies the algo to use if we have an incomplete path
                move = get_ship_nav_move(game, ship, "astar", {"move_cost": "turns"})
                if DEBUG & (DEBUG_GAME): logging.info("GAME - Ship {} is transiting {}".format(ship.id, move))

            command_queue.append(ship.move(move))
        else:
            #
            # mining
            #
            if DEBUG & (DEBUG_GAME): logging.info("GAME - Ship {} is mining".format(ship.id))
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

    # check if we can spawn a ship
    if ships_are_spawnable(game):
        command_queue.append(me.shipyard.spawn())
        if DEBUG & (DEBUG_GAME): logging.info("Game - Ship spawn request")

    #
    # collenct game metrics
    #
    game_metrics["profit"].append((game.turn_number, turn_gathered - turn_spent))
    game_metrics["time"].append((game.turn_number, round(time.time() - turn_start_time, 4)))

    #
    # debug info for each turn
    #

    # check of lost ships
    for ship_id in ship_states:
        if not me.has_ship(ship_id):
            if DEBUG & (DEBUG_GAME): logging.info("Game - Ship {} lost. Last seen on turn {}".format(ship_id, ship_states[ship_id]["last_seen"]))

    if DEBUG & (DEBUG_COMMANDS): logging.info("Game - command queue: {}".format(command_queue))

    if DEBUG & (DEBUG_SHIP_STATES): logging.info("Game - end ship_states: {}".format(ship_states))

    if DEBUG & (DEBUG_GAME_METRICS):
        mined_this_turn = sum(map(lambda i: i[2] if i[0] == game.turn_number else 0, game_metrics["mined"]))
        logging.info("Game - Mined this turn: {}".format(mined_this_turn))
        logging.info("Game - Mining rate: {}".format(round(get_mining_rate(game, 25), 2)))

    if DEBUG & (DEBUG_GAME_METRICS):
        logging.info("Game - Min turn time: {}".format(min(game_metrics["time"], key = lambda t: t[1])))
        logging.info("Game - Max turn time: {}".format(max(game_metrics["time"], key = lambda t: t[1])))
        logging.info("Game - Avg turn time: {:.4f}".format(np.mean(game_metrics["time"], axis=0)[1]))

        #logging.info("Game - Mined: {}".format(game_metrics["mined"]))
        logging.info("Game - Total mined: {}".format(sum(x[2] for x in game_metrics["mined"])))

        #logging.info("Game - Gathered: {}".format(game_metrics["gathered"]))
        logging.info("Game - Total gathered: {}".format(sum(x[2] for x in game_metrics["gathered"])))

        #logging.info("Game - Burned: {}".format(game_metrics["burned"]))
        logging.info("Game - Total burned: {}".format(sum(x[2] for x in game_metrics["burned"])))

        # profit = gathered - spent
        logging.info("Game - Profit: {}".format(sum(x[1] for x in game_metrics["profit"])))

    if DEBUG & (DEBUG_GAME_METRICS):
        mined_by_ship= {}
        avg_mined_by_ship = {}
        oldest_turn = 1 if game.turn_number < MINING_RATE_LOOKBACK else (game.turn_number - MINING_RATE_LOOKBACK)
        i = len(game.game_metrics["mined"]) - 1
        while i >= 0 and game.game_metrics["mined"][i][0] >= oldest_turn:
            s_id = game.game_metrics["mined"][i][1]
            halite = game.game_metrics["mined"][i][2]
            mined_by_ship[s_id] = (mined_by_ship[s_id] + halite) if s_id in mined_by_ship else halite
            i -= 1

        for s_id, halite in mined_by_ship.items():
            avg_mined_by_ship[s_id] = halite / (game.turn_number - game.ship_christenings[s_id] - 1)

        logging.info("Game - Ship mining rate averages (Last {} turns):".format(MINING_RATE_LOOKBACK))
        for s_id in avg_mined_by_ship:
            logging.info("Game - {:4d}: {}".format(s_id, round(avg_mined_by_ship[s_id], 2)))

        logging.info("Game - Ship yields (Last {} turns):".format(MINING_RATE_LOOKBACK))
        for s_id, halite in mined_by_ship.items():
            logging.info("Game - {:4d}: {}".format(s_id, halite))

    if DEBUG: logging.info("Game - Turn time: {}".format(round(time.time() - turn_start_time, 4)))

    #
    # last turn output
    #
    if game.turn_number == constants.MAX_TURNS:
        if DEBUG & (DEBUG_NAV_METRICS):
            logging.info("Nav - Loiter multiples: {}".format(game_metrics["loiter_multiples"]))
            logging.info("Nav - Loiter offsets: {}".format(game_metrics["loiter_offsets"]))
            logging.info("Nav - Loiter distances: {}".format(game_metrics["loiter_distances"])) # raw_loiter_point
            logging.info("Nav - Raw loiter points: {}".format(game_metrics["raw_loiter_points"]))

            avg_duration = np.mean(game_metrics["return_duration"], axis=0)[1]
            logging.info("Game - Avg. ship return duration: {}".format(round(avg_duration, 2)))

        if DEBUG & (DEBUG_GAME_METRICS):
            logging.info("Game - Min turn time: {}".format(min(game_metrics["time"], key = lambda t: t[1])))
            logging.info("Game - Max turn time: {}".format(max(game_metrics["time"], key = lambda t: t[1])))
            logging.info("Game - Avg turn time: {:.4f}".format(np.mean(game_metrics["time"], axis=0)[1]))

        if DEBUG & (DEBUG_OUTPUT_GAME_METRICS):
            dump_stats(game, game_metrics, "all")

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)


