#
#
#

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction

# convert a Direction obj back to a string
DIRECTIONS = {
    "n": Direction.North,
    "s": Direction.South,
    "e": Direction.East,
    "w": Direction.West
}

MIN_LOITER = 4
MAX_LOITER = 64