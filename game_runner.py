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
#    "python3.6 bots/cover-dropoff2/MyBot.py"
]

# True = 4p with oppenent shuffle, False = 2p
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

#seed = 1547320475

# @64 has dropoff area in upper corner (0, 8). First ships arrive here around 275
# seed = 1547489576

# @64 dense map, 915k halite. Drops (16,10)@t125, (0,48)@t200, (32,48)@?
#seed = 1547491166

# @32 good example of early dropoff (0,16)@t1 ... and totally failing
#seed =1547508173

# @48 medium good placement (8, 25)@t125 produces predicable wins by 10k
#seed = 1547513975

# @48 413K halite, good placement (8, 40)@200 produces wins by 15k
# opt #2 (4, 36)@150, (24,42)@250 ... with order backward win by 8k

# 1547618229 444k more halite better for dropoffs?

#1547618661 299k very distinct areas. consistent wins. Good to dev map reshape strat?

# 1547619884 437k generally dense

# 1547653248 320k good board edge areas

# 760k clusters around each base in 4p 64 and to a lesser extent @56
#seed = 1547674870

# 458k dense "X"
#seed = 1547766731

# 176k @32 2p dense, win by 10k!
#seed = 1547775491

arg_seed = ["--seed " + str(seed)] if seed else []

# @32 2p lose by 47k to 40k
#seed = 1547774601

arg_config = "-c halite-config.no-inspire.json"

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
