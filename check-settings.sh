#!/bin/bash
#


#for databaseName in a b c d e f; do
# do something like: echo $databaseName
#done

declare -a arr=("candidate.x" "bots/v23")

for botRoot in "${arr[@]}"
do
    echo "Bot: $botRoot"
    retval=$(cat $botRoot/myutils/constants.py | grep -i USE_CELL_VALUE_MAP)
    echo "  $retval"
    retval=$(cat $botRoot/myutils/constants.py | grep "DEBUG =")
    echo "  $retval"
done

