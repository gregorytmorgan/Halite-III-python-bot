#
#
#

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction

DEBUG_NONE = 0
DEBUG_GAME = 1
DEBUG_SHIP = 2
DEBUG_NAV = 4
DEBUG_NAV_METRICS = 8
DEBUG_GAME_METRICS = 16
DEBUG_COMMANDS = 32
DEBUG_SHIP_STATES = 64
DEBUG_OUTPUT_GAME_METRICS = 128

DEBUG_ALL = DEBUG_GAME | DEBUG_SHIP | DEBUG_NAV | DEBUG_NAV_METRICS | DEBUG_GAME_METRICS | DEBUG_COMMANDS | DEBUG_SHIP_STATES | DEBUG_OUTPUT_GAME_METRICS

DEBUG = DEBUG_GAME | DEBUG_GAME_METRICS | DEBUG_SHIP_STATES | DEBUG_NAV | DEBUG_NAV_METRICS |  DEBUG_OUTPUT_GAME_METRICS

# convert a Direction obj back to a string
DIRECTIONS = {
    "n": Direction.North,
    "s": Direction.South,
    "e": Direction.East,
    "w": Direction.West,
    "o": Direction.Still
}

MIN_LOITER = 4
MAX_LOITER = 64

MIN_SHIPS = 2
MAX_SHIPS = 2

STATS_DIR = 'stats'

MINING_RATE_LOOKBACK = 25
MINING_THRESHOLD_MULT = .1

DEPARTURE_DISTANCE = MIN_LOITER - 1


