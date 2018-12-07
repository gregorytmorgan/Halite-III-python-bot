import json
import logging
import sys
import numpy as np

from .common import read_input
from . import constants
from .game_map import GameMap, Player

from myutils.constants import DEBUG, DEBUG_NONE

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
        self.collisions = []
        self.command_queue = {},
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

        self.ship_christenings = {}

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

    def get_mining_rate(self, turns = None, ship_id = None):
        '''
        Returns the mining rate for the game or a specific ship. Always returns
        a rate of at least 1.
        '''
        if not self.game_metrics["mined"]:
            self.game_map.mean_halite * .25

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

        return rate

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
