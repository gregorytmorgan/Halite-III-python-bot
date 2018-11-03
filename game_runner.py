#!/usr/bin/env python3
# Python 3.6ls

import subprocess

arg_replay = "--replay-directory replays/"
arg_verbosity = "-vvv"
arg_width = "--width 32"
arg_height = "--height 32"
bot1_args = "python3 MyBot.py"
bot2_args = "python3 MyBot.py"
#arg_strict = "--strict"

args = ["./halite", arg_replay, arg_verbosity, arg_width, arg_height, bot1_args, bot2_args]

# run is only available in python 3.5+, prior use subprocess.call
retval = subprocess.run(args, stdout=subprocess.PIPE)

#subprocess.call(["./halite", "--replay-directory replays/ -vvv --width 32 --height 32 \"python3 MyBot.py\" \"python3 MyBot.py\"", "/dev/null"], stdout=subprocess.PIPE)

# CompletedProcess(args=['./halite', '--replay-directory replays/', '-vvv', '--width 32', '--height 32', 'python3 MyBot.py', 'python3 MyBot.py'], returncode=0, stdout=b'')

if retval.returncode != 0:
	print(str(args[0]) + " exited with code " + str(retval.returncode))
	if retval.stderr != None:
		print(retval.stderr.decode('utf-8'))
