#!/bin/bash
#

if [ -z "$1" ]; then
    echo "Candidate number required"
    exit 1
fi

n=$1

Candidate="candidate.$n"

if [ -e $Candidate ]; then
    echo "$Candidate already exists"
    exit 2
fi

mkdir $Candidate
retval=$?

if [ $retval != 0 ]; then
    echo "mkdir failed with error code $retval"
    exit 3
fi

cp MyBot.py $Candidate
retval=$?
if [ $retval != 0 ]; then
    echo "copy MyBot.py failed with error code $retval"
    exit 4
fi

cp -r hlt $Candidate
retval=$?
if [ $retval != 0 ]; then
    echo "Copy of hlt directory failed with error code $retval"
    exit 5
fi

cp -r myutils $Candidate
retval=$?
if [ $retval != 0 ]; then
    echo "Copy of myutils directory failed with error code $retval"
    exit 6
fi

if [ "$2" != "" ]; then
	echo $2 > $Candidate/readme.txt
fi

./manager.py -A candidate.$n -p "python3 candidate.$n/MyBot.py"

sed -i '/botName = /c\botName = \"candidate.'$n\" $Candidate/MyBot.py

echo "$Candidate done."







