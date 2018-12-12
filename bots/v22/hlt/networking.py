import json
import logging
import sys
import numpy as np

from .common import read_input
from . import constants
from .game_map import GameMap, Player

from hlt.positionals import Position
from hlt.entity import Ship

from myutils.constants import SHIP_MINING_EFFICIENCY, SHIP_MAX_HALITE, DEBUG, DEBUG_NONE
from myutils.globals import Mining_threshold

class Game:
    """
    The game object holds all metadata pertinent to the game and all its contents
    """
    def __init__(self):
        """
        Initiates a game object collecting all start-state instances for the contained items for pre-game.
        Also sets up basic logging.
        """
        self.turn_number = 0

        # (this_ship, offending_ship, move, collision_position, resolution_function)
        self.collisions = []

        # metrics
        self.game_metrics = {
            "burned": [],
            "gathered": [(0, 0, 5000)],
            "loiter_distances": [],
            "loiter_multiples": [],
            "loiter_offsets": [],
            "mined": [],
            "profit": [],
            "raw_loiter_points": [],
            "trip_transit_duration": [],
            "trip_explore_duration": [],
            "spent": [],
            "trip_data": [],
            "turn_time": []
        }

        # keyed on ship id
        self.command_queue = {}

        # keyed on ship id. We can't attach a christening attrib to a ship obj because
        # we'll lose the info if the ship is destroyed. We're interested in destroyed ship
        # info when we calc stats such as overall mining rate
        self.ship_christenings = {}

        # keyed on position
        self.loiter_assignments = {}

        # Grab constants JSON
        raw_constants = read_input()
        constants.load_constants(json.loads(raw_constants))

        num_players, self.my_id = map(int, read_input().split())

        if DEBUG != DEBUG_NONE:
            logging.basicConfig(
                filename="bot-{}.log".format(self.my_id),
                filemode="w",
                level=logging.DEBUG
            )

        self.players = {}
        for player in range(num_players):
            self.players[player] = Player._generate()
        self.me = self.players[self.my_id]
        self.game_map = GameMap._generate()

    def ready(self, name):
        """
        Indicate that your bot is ready to play.
        :param name: The name of your bot
        """
        send_commands([name])

    def update_frame(self):
        """
        Updates the game object's state.
        :returns: nothing.
        """
        self.turn_number = int(read_input())
        logging.info("=============== TURN {:03} ================".format(self.turn_number))

        for _ in range(len(self.players)):
            player, num_ships, num_dropoffs, halite = map(int, read_input().split())
            self.players[player]._update(num_ships, num_dropoffs, halite)

        self.game_map._update()

        # Mark cells with ships as unsafe for navigation
        for player in self.players.values():
            for ship in player.get_ships():
                self.game_map[ship.position].mark_unsafe(ship)

            self.game_map[player.shipyard.position].structure = player.shipyard
            for dropoff in player.get_dropoffs():
                self.game_map[dropoff.position].structure = dropoff

    def turns_to_mining_threshold(self, initial_halite, threshold):
        """
        Get the number of turns to reach the remaining halite threshold from initial_halite

        THIS IS A HACK, should have actual func to determine turns to threshold
        """
        t = 1

        if initial_halite <= threshold:
            return 0

        remaining = initial_halite

        while remaining > threshold:
            remaining = initial_halite - self.mining_value(initial_halite, t)
            t += 1

        return t

    def turns_to_mining_yield(self, initial_halite, target):
        """
        Get the number of turns to reach yield y (halite value) from initial_halite.

        E.g. how many turns until I'm getting < 100 halite per turn?
        """
        return 1 + math.log(float(target)/initial_halite, SHIP_MINING_EFFICIENCY)

    def mining_value(self, initial_halite, t):
        """
        Get the total amount of halite mined at turn t when starting with initial_halite.

        :param initial_halite Initial halite in the cell at the start of mining
        :param t Time/turns mined.s
        :return Total halite mined.
        """
        return initial_halite - (initial_halite * (1 - SHIP_MINING_EFFICIENCY) ** t)

    def get_mining_rate(self, turns = None, ship_id = None):
        '''
        Returns the mining rate for the game or a specific ship. Always returns
        a rate of at least 1.
        '''
        if len(self.game_metrics["mined"]) < 3:
            row_start = self.me.shipyard.position.y - 3
            row_end = self.me.shipyard.position.y + 3
            col_start = self.me.shipyard.position.x - 3
            col_end = self.me.shipyard.position.x + 3

            shipyard_area_mean_halite = np.mean(self.game_map._halite_map[row_start:row_end, col_start:col_end])

            logging.debug("shipyard_area_mean_halite: {}".format(shipyard_area_mean_halite))
            logging.debug("avg minable halite per cell: {}".format(shipyard_area_mean_halite - Mining_threshold))

            #m = SHIP_MAX_HALITE / (shipyard_area_mean_halite - Mining_threshold)
            #logging.debug("m: {}".format(m))

            t = self.turns_to_mining_threshold(shipyard_area_mean_halite, Mining_threshold)

            logging.debug("turns: {}".format(t))

            if t == 0:
                mrate = 1.0
            else:
                mrate = (shipyard_area_mean_halite - Mining_threshold) / t

            logging.debug("mrate: {}".format(mrate))

            return max(1.0, mrate)

        if turns is None:
            turns = self.turn_number

        oldest_turn = 1 if self.turn_number < turns else (self.turn_number - turns)
        i = len(self.game_metrics["mined"]) - 1

        mined = []
        mined_by_ship = {}

        # turn, ship.id, mined
        while i >= 0 and self.game_metrics["mined"][i][0] > oldest_turn:
            s_id = self.game_metrics["mined"][i][1]
            halite = self.game_metrics["mined"][i][2]
            mined_by_ship[s_id] = mined_by_ship[s_id] + halite if s_id in mined_by_ship else halite
            i -= 1

        if ship_id is None:
            for s_id, halite in mined_by_ship.items():
                mined.append(halite / (self.turn_number - self.ship_christenings[s_id] - 1))

            rate = np.average(mined)
        else:
            rate = mined_by_ship.items[ship_id] / (self.turn_number - self.ship_christenings[ship_id] - 1)

        return max(1, rate)

    def get_loiter_assignment(self, target):
        """
        Get a loiter assignment by ship or point.

        :param loiter_assignments List of assignments
        :param target Ship|Position
        :return Tuple (Position, ship_id) on success, False otherwise
        """
        if isinstance(target, Ship):
            for pt, sid in self.loiter_assignments.items():
                if sid == target.id:
                    return (pt, sid)
        elif isinstance(target, Position):
            if target in self.loiter_assignments:
                return (target, self.loiter_assignments[target])

        return False

    def update_loiter_assignment(self, target, loiter_point = None):
        """
        Add/remove a loiter assignment by ship or Position.

        If the 2nd arg is present, then it's an assignment, otherwise it's a deletion.

        :param loiter_assignments List of assignments
        :param target Ship|Position
        :param loiter_point
        :return True on success, False otherwise
        """

        if loiter_point:
            self.loiter_assignments[loiter_point] = target.id
            retval = True
        else:
            unassigned_point = False
            if isinstance(target, Ship):
                for pt, sid in self.loiter_assignments.items():
                    if sid == target.id:
                        unassigned_point = pt
                        break
            elif isinstance(target, Position):
                if target in self.loiter_assignments:
                    sid = self.loiter_assignments[target]
                    unassigned_point = target

            if unassigned_point:
                self.loiter_assignments.pop(unassigned_point, None)
                retval = True
            else:
                retval = False

        return retval

    @staticmethod
    def end_turn(commands):
        """
        Method to send all commands to the game engine, effectively ending your turn.
        :param commands: Array of commands to send to engine
        :return: nothing.
        """
        send_commands(commands)


def send_commands(commands):
    """
    Sends a list of commands to the engine.
    :param commands: The list of commands to send.
    :return: nothing.
    """
    print(" ".join(commands))
    sys.stdout.flush()
