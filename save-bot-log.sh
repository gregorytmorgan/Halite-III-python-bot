#!/bin/bash

tstamp=$(date +"%s")
botlog="bot-0.log"

if [ -z $1 ]; then
	seed=$tstamp
else
	seed=$1
fi

if [ ! -d "logs" ]; then
	/bin/mkdir -p logs
fi

/bin/cp $botlog logs/bot-log-0.$seed.log
retval=$?

if [ "$retval" != "0" ]; then
	/bin/echo "Log copy failed with error code $retval"
fi

