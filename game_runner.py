#!/usr/bin/env python3
# Python 3.6ls

import subprocess
import sys

arg_replay = "--replay-directory replays/"
arg_verbosity = "-vvv"
arg_width = "--width 40"
arg_height = "--height 40"

bot1_args = "python3 MyBot.py"
bot2_args = "python3 bots/v15/MyBot.v15.py"

#bot1_args = "python3 candidate.v15.4/MyBot.py"
#bot2_args = "python3 candidate.v15.3/MyBot.py"

#bot3_args = "python3 bots/MyBot.v10.py"
#bot4_args = "python3 bots/MyBot.v9.py"

#arg_strict = "--strict"
arg_seed = "--seed 1543005624" # small sparse, v15 loses
arg_seed = "--seed 1543007974" # small sparse, v15 loses
arg_seed = "--seed 1543014634" # dense map with deadlock waiting to dropoff

arg_seed = "--seed 1543094899" # dense map


# base jam: 64x64, Map seed is 1541367798
# base jam: 64x64, Map seed is 1541450737 ???
# 64x64 4 player 1541450737 # stuck at turn ~82
# 64x64, 4 player, 1541460138, opponent collision at turn 422
# , bot3_args, bot4_args
# , arg_width, arg_height
args = ["./halite",  arg_replay, arg_verbosity, bot1_args, bot2_args]

# run is only available in python 3.5+, prior use subprocess.call
retval = subprocess.run(args, stdout=subprocess.PIPE, stderr=sys.stderr)

if retval.returncode != 0:
    print(str(args[0]) + " exited with code " + str(retval.returncode))
    if retval.stderr != None:
        print(retval.stderr.decode('utf-8'))
