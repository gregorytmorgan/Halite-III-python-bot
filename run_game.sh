#!/bin/sh

if [ -z "$1" ]; then
   ./halite --replay-directory replays/ -vvv --width 32 --height 32 "python3.6 MyBot.py" "python3.6 MyBot.py"
else
	./halite --replay-directory replays/ -vvv --width 32 --height 32 "python3.6 $1" "python3.6 $1"
fi

