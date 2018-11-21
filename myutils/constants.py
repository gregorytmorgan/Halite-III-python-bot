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
DEBUG_STATES = 64
DEBUG_OUTPUT_GAME_METRICS = 128

DEBUG_ALL = DEBUG_GAME | DEBUG_SHIP | DEBUG_NAV | DEBUG_NAV_METRICS | DEBUG_GAME_METRICS | DEBUG_COMMANDS | DEBUG_STATES | DEBUG_OUTPUT_GAME_METRICS

DEBUG = DEBUG_GAME | DEBUG_SHIP | DEBUG_NAV | DEBUG_STATES

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

MAX_SHIPS = 24

STATS_DIR = 'stats'