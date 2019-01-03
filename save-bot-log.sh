#!/bin/bash

tstamp=$(date +"%s")
botlog="bot-0.log"


files=$(ls -rt1 bot-?.log)



if [ -z $1 ]; then
	tag=$tstamp
else
	tag=$1
fi

# override the tag for now
#tag=$tstamp

if [ ! -d "logs" ]; then
	/bin/mkdir -p logs
fi

for f in $files; do

    /bin/mv $f logs/$f.$tag
    retval=$?

    if [ "$retval" != "0" ]; then
	/bin/echo "$f move failed with error code $retval"
    fi
    
done
