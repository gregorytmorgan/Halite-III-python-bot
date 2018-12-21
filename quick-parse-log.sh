#!/bin/bash
#

if [ -z "$1" ]; then
    file="bot-0.log"
else
    file=$1
fi

if [ ! -e $file ]; then
    echo "File does not exists $file"
    exit 1
fi

retval=$(cat $file | grep -i "warning" | wc -l)
echo "$retval warnings"

retval=$(cat $file | grep -i "error" | wc -l)
echo "$retval errors"

retval=$(cat $file | grep "No targets remain" | wc -l)
echo "$retval No targets remain"

retval=$(cat $file | grep "exceeds available targets" | wc -l)
echo "$retval exceeds available targets"

retval=$(cat $file | grep "SKIPPED MINING" | wc -l)
echo "$retval SKIPPED MINING"

#retval=$(cat $file | grep "No retask" | wc -l)
#echo "$retval No retask"

#retval=$(cat $file | grep "Retask" | wc -l)
#echo "$retval Retask"

retval=$(cat $file | grep "has a short mining rate" | wc -l)
echo "$retval mining threshold below cell halite (has a short mining rate)"

retval=$(cat $file | grep "Best block search failed" | wc -l)
echo "$retval Best block search failed"

retval=$(cat $file | grep "cells have halite < threshold" | wc -l)
echo "$retval cells have halite < threshold"

retval=$(cat replays/errorlog*.log | grep "owned entities" | grep "collided" | wc -l)
echo "$retval cat replays/errorlog*.log | grep 'owned entities' | grep 'collided'"
