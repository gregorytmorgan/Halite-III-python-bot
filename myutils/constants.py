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

# To view profiling ./analyze_stats.py profiler_results.dmp profiling_results.txt
DEBUG_PROFILING = 4096

DEBUG_ALL = DEBUG_GAME | DEBUG_TIMING | DEBUG_NAV | DEBUG_NAV_METRICS | DEBUG_GAME_METRICS \
    | DEBUG_COMMANDS | DEBUG_SHIP_STATES | DEBUG_OUTPUT_GAME_METRICS | DEBUG_CV_MAP | DEBUG_TASKS \
    | DEBUG_NAV_VERBOSE | DEBUG_SHIP_METRICS | DEBUG_PROFILING

DEBUG = DEBUG_NONE #DEBUG_GAME | DEBUG_TIMING| DEBUG_NAV | DEBUG_OUTPUT_GAME_METRICS | DEBUG_GAME_METRICS | DEBUG_TASKS | DEBUG_SHIP_STATES

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

CV_MAP_THRESHOLD_DEFAULT = 0
CV_MAP_THRESHOLD_STEP = 25
CV_MAP_THRESHOLD_MIN = -(CV_MAP_THRESHOLD_STEP * 10)

BLOCKED_BY_THRESHOLD_FRIENDLY = 16
BLOCKED_BY_THRESHOLD = 4
PROXIMITY_BLOCKED_BY_THRESHOLD = 4

LOG_DIRECTORY = "."
#LOG_DIRECTORY = "logs"

# Scale 'payback' turns. Decide if a spawned ship will have enough time to pay for
# itself. Lower number == spawn ships for longer == more ships.
#
# - Related to CV_MINING_RATE_MULTIPLIER in that the higher the rate, the longer we can spawn.
# - This is also a func of board size, for smaller boards at some point more ship are useless.
MINING_OVERHEAD_CONGESTED = 3.0
MINING_OVERHEAD_OPEN = 2.0
MINING_OVERHEAD_DEFAULT = 2.5

# how many turns to allow a homing ship to get to base
HOMING_OVERHEAD = 1.5

# changes the value assigned to cell based on distance from base. This will
# change the steepness of 'mined' (change in minging rate) for a fix number of ships.
#
# - Related to MINING_OVERHEAD since the better the mining rate, the longer we can spawn
CV_MINING_RATE_MULTIPLIER_CONGESTED = .5
CV_MINING_RATE_MULTIPLIER_OPEN = 1.0
CV_MINING_RATE_MULTIPLIER_DEFAULT = .75

# how many data points before try to calc mining rate. Below this, just return the avg
# halite amount * SHIP_MINING_EFFICIENCY
MIN_MINE_RATE_DATA = 3

# commented out in code/not used - the minimum total value the positions in an peak area to consider
# it valid. 'value' could be halite, cv values, etc.
#DROPOFF_MIN_TOTAL_VALUE = 4000

# the minimum number of positions to consider a valid area
DROPOFF_AREA_MIN_POSITIONS = 2

# min value for COLLISION_AVOIDANCE_EXCHANGE_RATIO. Even f the enemy/friendly halite ratio exceeds
# COLLISION_AVOIDANCE_EXCHANGE_RATIO still avoid enemy ships if their halite < COLLISION_AVOIDANCE_THRESHOLD_MIN
COLLISION_AVOIDANCE_THRESHOLD_MIN = 800

# Ship halite amount at which friendly ship will not avoid enemy ships/ crash is ok if they have x more cargo
COLLISION_AVOIDANCE_EXCHANGE_RATIO = 4