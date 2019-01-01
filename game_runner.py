#!/usr/bin/env python3
# Python 3.6

import subprocess
import sys
import shutil
import time

arg_replay = "--replay-directory replays/"
arg_verbosity = "-vvv"
arg_width = "--width 32"
arg_height = "--height 32"

# pypy example, other than invoking with pypy3 no other changes are needed, though
# in the case of the halite.io server, an extension of .pypy is required
#bot1_args = "./pypy3 -E MyBot.py"

bot1_args = "python3 MyBot.py"
bot2_args = "python3 bots/v26/MyBot.py"
bot3_args = "python3 bots/v25/MyBot.py"
bot4_args = "python3 bots/v24/MyBot.v24.py"

#arg_strict = "--strict"
arg_seed = "--seed 1543014634" # dense map with deadlock waiting to dropoff
arg_seed = "--seed 1543094899" # dense map


# base jam: 64x64, Map seed is 1541367798
# base jam: 64x64, Map seed is 1541450737 ???
# 64x64 4 player 1541450737 # stuck at turn ~82
# 64x64, 4 player, 1541460138, opponent collision at turn 422
# , bot3_args, bot4_args
# , arg_width, arg_height
args = ["./halite", arg_replay, arg_verbosity, bot1_args, bot2_args, bot3_args, bot4_args, arg_width, arg_height]

# run is only available in python 3.5+, prior use subprocess.call
retval = subprocess.run(args, stdout=subprocess.PIPE, stderr=sys.stderr)

if retval.returncode != 0:
    print(str(args[0]) + " exited with code " + str(retval.returncode))
    if retval.stderr != None:
        print(retval.stderr.decode('utf-8'))

shutil.copyfile("bot-0.log",  "logs/bot-0." + str(round(time.time())) + ".log")
