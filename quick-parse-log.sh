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

#retval=$(cat replays/errorlog*.log | grep "owned entities" | grep "collided" | wc -l)
#echo "$retval cat replays/errorlog*.log | grep 'owned entities' | grep 'collided'"

retval=$(cat $file | grep -i "warning" | wc -l)
echo "$retval cat $file | grep -i 'warning'"

retval=$(cat $file | grep -i "error" | wc -l)
echo "$retval cat $file | grep -i 'error'"

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

retval=$(cat $file | grep "Best block search failed 1" | wc -l)
echo "$retval Best block search failed 1"

retval=$(cat $file | grep "Best block search failed 2" | wc -l)
echo "$retval Best block search failed 2"

retval=$(cat $file | grep "cells have halite < threshold" | wc -l)
echo "$retval cells have halite < threshold"

retval=$(cat $file | grep -i "Sos recieved" | wc -l)
echo "$retval cat $file | grep -i 'Sos recieved'"

retval=$(cat $file | grep -i "Sos disregarded" | wc -l)
echo "$retval cat $file | grep -i 'Sos disregarded'"

retval=$(cat $file | grep -i sos | grep -i "no viable" | wc -l)
echo "$retval cat $file | grep -i sos | grep -i 'no viable'"

retval=$(cat $file | grep -i sos | grep -i "diverted from assignment" | wc -l)
echo "$retval cat $file | grep -i sos | grep -i 'diverted from assignment'"

retval=$(cat $file | grep -i sos | grep -i "assigned to respond" | wc -l)
echo "$retval cat $file | grep -i sos | grep -i 'assigned to respond'"


