#!/bin/bash

TargetFile=$(ls -t -1  ~/dev/Halite-III-python-bot/replays/*.hlt | tail -1)

/usr/local/bin/electron /home/gmorgan/dev/fluorine -o  $TargetFile



