#!/bin/bash
#

if [ -z "$1" ]; then
    echo "Ship required"
    exit 1
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

initial="assigned loiter"
milestones="completed assignment\|now returning\|reached loiter\|did not reach loiter\|approached loiter"
sos="assigned to respond\|diverted from assignment"
terminal="completed dropoff\|lost"

cat $file | grep -i "$ship" | grep -i "$initial\|$milestones\|$terminal"