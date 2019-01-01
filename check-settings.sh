#!/bin/bash
#

for botRoot in ${BASH_ARGV[*]}; do

    echo "Bot: $botRoot"
    retval=$(cat $botRoot/myutils/constants.py | grep -i USE_CELL_VALUE_MAP)
    echo "  $retval"

    retval=$(cat $botRoot/myutils/constants.py | grep "DEBUG =")
    echo "  $retval"

    #retval=$(cat $botRoot/myutils/constants.py | grep "MINING_OVERHEAD_.. =")
    #echo "  $retval"

    retval=$(cat $botRoot/myutils/constants.py | grep "MAX_SHIPS =")
    echo "  $retval"

done

