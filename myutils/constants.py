#
#
#

# No debug messages
DEBUG_NONE = 0

# General game flow
DEBUG_GAME = 1

# Misc timings. Complete game, game initialization (cv map), turn, A* path calc
DEBUG_TIMING = 2

# Detailed logging on path generation
DEBUG_NAV = 4

# Misc nav related metrics, loiter pt multiples and location, Return trip duration, ...
DEBUG_NAV_METRICS = 8

# Misc game metrics. Total: Mined, gathered, burned, profit, spent. Turn: Mined gathered,
# burned, profit, spent, mining rate.  cv Map,
DEBUG_GAME_METRICS = 16

# Command queue
DEBUG_COMMANDS = 32

# Ship states
DEBUG_SHIP_STATES = 64

# Write the game meterics to a file for analysis
DEBUG_OUTPUT_GAME_METRICS = 128

DEBUG_ALL = DEBUG_GAME | DEBUG_TIMING | DEBUG_NAV | DEBUG_NAV_METRICS | DEBUG_GAME_METRICS | DEBUG_COMMANDS | DEBUG_SHIP_STATES | DEBUG_OUTPUT_GAME_METRICS

DEBUG = DEBUG_NONE # DEBUG_GAME | DEBUG_GAME_METRICS | DEBUG_NAV | DEBUG_OUTPUT_GAME_METRICS | DEBUG_SHIP_STATES | DEBUG_TIMING

# convert a Direction obj back to a string
DIRECTIONS = {
    "n": (0, -1),
    "s": (0, 1),
    "e": (1, 0),
    "w": (-1, 0),
    "o": (0, 0)
}

MIN_LOITER = 4
MAX_LOITER = 64

MIN_SHIPS = 4
MAX_SHIPS = 24

STATS_DIR = 'stats'

MINING_RATE_LOOKBACK = 25
MINING_THRESHOLD_MULT = .1

DEPARTURE_DISTANCE = MIN_LOITER - 1

# Spawn ship up to EXPEDITED_SHIP_COUNT regardless of any other spawn constraints
EXPEDITED_SHIP_COUNT = 4
EXPEDITED_DEPARTURE = False

USE_CELL_VALUE_MAP = True


