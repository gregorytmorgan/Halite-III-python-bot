#!/usr/bin/env python3
# Python 3.6

import subprocess
import sys
import shutil
import time
import random

arg_replay = "--replay-directory replays/"
arg_verbosity = "-vvv"
arg_width = "--width 32"
arg_height = "--height 32"

# pypy example, other than invoking with pypy3 no other changes are needed, though
# in the case of the halite.io server, an extension of .pypy is required
#bot1_args = "./pypy3 -E MyBot.py"

bot1_args = "python3 MyBot.py"

opponents = [
	"python3 bots/v26/MyBot.py",
	"python3 bots/v25/MyBot.py",
	"python3 bots/v24/MyBot.v24.py"
]

# shuffle the oppenents so board layout changes

oppenent_count = len(opponents)

idx = random.randint(1, oppenent_count)

bot2_args = opponents[idx  % oppenent_count]
bot3_args = opponents[(idx + 1)  % oppenent_count]
bot4_args = opponents[(idx + 2)  % oppenent_count]

#arg_strict = "--strict"
arg_seed = "--seed 1543014634" # dense map, 301k halite
#arg_seed = "--seed 1543094899" # dense map, 265k halite, dense around base

# , bot3_args, bot4_args
# , arg_width, arg_height
args = ["./halite", arg_seed, arg_replay, arg_verbosity, bot1_args, bot2_args, bot3_args, bot4_args, arg_width, arg_height]

# run is only available in python 3.5+, prior use subprocess.call
retval = subprocess.run(args, stdout=subprocess.PIPE, stderr=sys.stderr)

if retval.returncode != 0:
    print(str(args[0]) + " exited with code " + str(retval.returncode))
    if retval.stderr != None:
        print(retval.stderr.decode('utf-8'))

shutil.copyfile("bot-0.log",  "logs/bot-0." + str(round(time.time())) + ".log")
