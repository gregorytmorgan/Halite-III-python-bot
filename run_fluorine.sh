#!/bin/bash

TargetFile=$(ls -r -t -1  ~/dev/Halite-III-python-bot/replays/*.hlt | tail -1)


if [ -f /usr/local/bin/electron ]; then
    ELECTRON=/usr/local/bin/electron
elif [ -f node_modules/.bin/electron ]; then 
    ELECTRON=node_modules/.bin/electron
else
    echo 'Electron not found'
    exit 1
fi

$ELECTRON /home/gmorgan/dev/fluorine -o  $TargetFile



