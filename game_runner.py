#!/usr/bin/env python3
# Python 3.6

import subprocess
import sys

arg_replay = "--replay-directory replays/"
arg_verbosity = "-vvv"
arg_width = "--width 32"
arg_height = "--height 32"

# pypy example, other than invoking with pypy3 no other changes are needed, though
# in the case of the halite.io server, an extension of .pypy is required
#bot1_args = "./pypy3 -E MyBot.py"

bot1_args = "python3 MyBot.py"
bot2_args = "python3 bots/v18/MyBot.v18.py"
bot3_args = "python3 bots/v17/MyBot.v17.py"
bot4_args = "python3 bots/v16/MyBot.v16.py"

#arg_strict = "--strict"
arg_seed = "--seed 1543014634" # dense map with deadlock waiting to dropoff
arg_seed = "--seed 1543094899" # dense map


# base jam: 64x64, Map seed is 1541367798
# base jam: 64x64, Map seed is 1541450737 ???
# 64x64 4 player 1541450737 # stuck at turn ~82
# 64x64, 4 player, 1541460138, opponent collision at turn 422
# , bot3_args, bot4_args
# , arg_width, arg_height
args = ["./halite", arg_replay, arg_verbosity, bot1_args, bot2_args, arg_width, arg_height]

# run is only available in python 3.5+, prior use subprocess.call
retval = subprocess.run(args, stdout=subprocess.PIPE, stderr=sys.stderr)

if retval.returncode != 0:
    print(str(args[0]) + " exited with code " + str(retval.returncode))
    if retval.stderr != None:
        print(retval.stderr.decode('utf-8'))
