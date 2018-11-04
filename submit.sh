#!/bin/bash

VERSION_FILE="./version.txt"
MYBOT_FILE="./MyBot.py"
HLT_DIR="./hlt"

if [ ! -f $VERSION_FILE ]; then
	echo "No version file"
	exit 1
fi

if [ ! -f $MYBOT_FILE ]; then
	echo "No bot file"
	exit 2
fi

if [ ! -d $HLT_DIR ]; then
	echo "No hlt directory"
	exit 3
fi

Version=$(cat ./version.txt)

#
# delete old archive
#

ARCHIVE_NAME="MyBot.$Version.zip"

if [ -f $ARCHIVE_NAME ]; then
	rm -f $ARCHIVE_NAME
fi

#
# create new archive
#

echo "Incrementing version ..."

Version=$(expr $Version + 1)

echo "Incrementing version ... done."

ARCHIVE_NAME="MyBot.$Version.zip"

echo "Zipping ..."

/usr/bin/zip $ARCHIVE_NAME $MYBOT_FILE $VERSION_FILE $HLT_DIR
Retval=$?

if [ $Retval != 0 ]; then
	echo "Error - zip failed with error $Retval"
	exit 5
fi

echo "Zipping ... done."

echo "Uploading ..."

# python3 -m hlt_client bot -b MyBot.5.zip upload
python3 -m hlt_client bot -b $ARCHIVE_NAME upload

Retval=$?

if [ $Retval != 0 ]; then
	echo "Error - submit failed with error $Retval"
	exit 5
fi

echo "Uploading ... done."

echo "Updating version file ..."

echo $Version > $VERSION_FILE

echo "Updating version file ... done."

echo "Done."


