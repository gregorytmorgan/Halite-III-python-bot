#!/bin/bash
#

function usage () {
    echo "Usage: $(basename $0) ship_id [log_file]"
}

if [ -z "$1" ]; then
    echo "Error: ship_id required"
    usage
    exit 1
elif [ "$1" == "-h" ]; then
    usage
    exit 0
else
    ship="ship $1 "
fi

if [ -z "$2" ]; then
    file="bot-0.log"
else
    file=$2
fi

if [ ! -e $file ]; then
    echo "File does not exists $file"
    exit 1
fi

initial="new ship\|assigned loiter\|using random loiter"
milestones="completed assignment\|now returning\|reached loiter\|did not reach loiter\|approached loiter"
sos="assigned to respond\|diverted from assignment"
terminal="completed dropoff\|lost\|now homing"

cat $file | grep -i "$ship" | grep -i "$initial\|$sos\|$milestones\|$terminal"
