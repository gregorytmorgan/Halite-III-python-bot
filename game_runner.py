#!/usr/bin/env python3.6

import subprocess
import sys
import shutil
import time
import random

print(sys.version)

arg_replay = "--replay-directory replays/"
arg_verbosity = "-vvv"
arg_width = "--width 48"
arg_height = "--height 48"

# pypy example, other than invoking with pypy3 no other changes are needed, though
# in the case of the halite.io server, an extension of .pypy is required
#bot1_args = "./pypy3 -E MyBot.py"

# Note: Nebeans has trouble running bots with diff versions of python.  Make sure the
# Netbeans python version matches the cmd line version
bot1_args = "python3.6 MyBot.py"

opponents = [
    "python3.6 bots/v26/MyBot.py",
    "python3.6 bots/v25/MyBot.py",
    "python3.6 bots/v27/MyBot.py"
]

# True = 4p with oppenent shuffle
if False:
    oppenent_count = len(opponents)
    idx = random.randint(0, oppenent_count) % oppenent_count
    bot2_args = opponents[idx]
    bot3_args = opponents[(idx + 1)  % oppenent_count]
    bot4_args = opponents[(idx + 2)  % oppenent_count]
    more_opponents = [bot3_args, bot4_args]
else:
    bot2_args = opponents[2]
    more_opponents = []

#arg_strict = "--strict"

seed = None
#seed = 543014634 # dense map, 301k halite
#seed = 1543094899 # dense map, 265k halite, dense around base
#seed = 1547265756
#seed = 1547280599 # good for dropoffs @64 , not so much @ 32

seed = 1547320475

arg_seed = ["--seed " + str(seed)] if seed else []

# , bot3_args, bot4_args
# , arg_width, arg_height
args = ["./halite", arg_replay, arg_verbosity, arg_width, arg_height, bot1_args, bot2_args] + more_opponents + arg_seed

# run is only available in python 3.5+, prior use subprocess.call
retval = subprocess.run(args, stdout=subprocess.PIPE, stderr=sys.stderr)

if retval.returncode != 0:
    print(str(args[0]) + " exited with code " + str(retval.returncode))
    if retval.stderr != None:
        print(retval.stderr.decode('utf-8'))

shutil.copyfile("bot-0.log",  "logs/bot-0." + str(round(time.time())) + ".log")
