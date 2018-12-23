#
#
#

from hlt import constants

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

# output the cv map to the log on early + last turns
DEBUG_CV_MAP = 256

#
DEBUG_TASKS = 512

# more detailed nav info
DEBUG_NAV_VERBOSE = 1024

# individual ship stats for mining rate, yield (halite collected), ...
DEBUG_SHIP_METRICS = 2048

DEBUG_ALL = DEBUG_GAME | DEBUG_TIMING | DEBUG_NAV | DEBUG_NAV_METRICS | DEBUG_GAME_METRICS \
    | DEBUG_COMMANDS | DEBUG_SHIP_STATES | DEBUG_OUTPUT_GAME_METRICS | DEBUG_CV_MAP | DEBUG_TASKS \
    | DEBUG_NAV_VERBOSE | DEBUG_SHIP_METRICS

DEBUG = DEBUG_NONE # DEBUG_GAME | DEBUG_TIMING| DEBUG_NAV | DEBUG_OUTPUT_GAME_METRICS | DEBUG_GAME_METRICS | DEBUG_TASKS

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

MAX_SHIPS = 128

STATS_DIR = 'stats'

MINING_RATE_LOOKBACK = 32
MINING_RATE_LOOKBACK_SHORT = 8

SHIP_MAX_HALITE = 1000 # MAX_HALITE = 1000

SHIP_FUEL_COST = .1

SHIP_MINING_THRESHOLD_DEFAULT = 100

SHIP_REFUEL_THRESHOLD = .95

SHIP_MINING_EFFICIENCY = .25

DEPARTURE_DISTANCE = MIN_LOITER - 1

# Spawn ship up to EXPEDITED_SHIP_COUNT regardless of any other spawn constraints
EXPEDITED_SHIP_COUNT = 4

USE_CELL_VALUE_MAP = True

TARGET_THRESHOLD_DEFAULT = 0
TARGET_THRESHOLD_STEP = 50
TARGET_THRESHOLD_MIN = -(TARGET_THRESHOLD_STEP * 10)

BLOCKED_BY_THRESHOLD_FRIENDLY = 16
BLOCKED_BY_THRESHOLD = 3

LOG_DIRECTORY = "."
LOG_DIRECTORY = "logs"
