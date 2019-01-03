#!/bin/bash
#

if [ -z "$1" ]; then
    echo "Usage: $0 bot_directory [bot_directory ...]"
fi

for botRoot in ${BASH_ARGV[*]}; do

    echo "Bot: $botRoot"
    retval=$(cat $botRoot/myutils/constants.py | grep -i "USE_CELL_VALUE_MAP")
    echo "  $retval"

    retval=$(cat $botRoot/myutils/constants.py | grep "DEBUG =")
    echo "  $retval"

    #retval=$(cat $botRoot/myutils/constants.py | grep "MINING_OVERHEAD_.. =")
    #echo "  $retval"

    retval=$(cat $botRoot/myutils/constants.py | grep "MAX_SHIPS =")
    echo "  $retval"
    
    retval=$(cat $botRoot/myutils/constants.py | grep "CV_MINING_RATE_MULTIPLIER =")
    echo "  $retval"

done

