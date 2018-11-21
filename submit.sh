#!/bin/bash
#
# To 'undo' a submission
#	1) delete bots/MyBot.v[version].py
#	2) delete archive/MyBot.v[version].zip
#	3) remove from manager

#
# Usage
#
show_help ()
{
	echo
	echo "Usage: submit.sh [-c cleanup_version | -s submit_version]"
	echo ""
	echo "Default is to submit based on version.txt". If both -c and -s, then -c.
}

#
# parse args
#
while getopts "h?vc:s:" opt; do
    case "$opt" in
    h|\?)
        show_help
        exit 0
        ;;
    v)  verbose=1
        ;;
    c)  cleanup_version=$OPTARG
        ;;
    s)  submit_version=$OPTARG
        ;;
    esac
done

shift $((OPTIND-1))

[ "${1:-}" = "--" ] && shift

echo "verbose=$verbose, cleanup_version='$cleanup_version', submit_version='$submit_version', Leftovers: $@"

#
# main
#

SUBMIT=0
PROJECT_ROOT=$(pwd)
BOT_DIR="$PROJECT_ROOT/bots"
ARCHIVE_DIR="$PROJECT_ROOT/archive"

# note: don't use full path for files included in the archive
VERSION_FILE="version.txt"
MYBOT_FILE="MyBot.py"
HLT_DIR="hlt"
UTIL_DIR="myutils"
EXCLUDES="hlt/__pycache__/\* myutils/__pycache__/\*"


if [ ! -f $VERSION_FILE ]; then
	echo "No $VERSION_FILE file"
	exit 1
fi

if [ ! -f $MYBOT_FILE ]; then
	echo "No $MYBOT_FILE file"
	exit 2
fi

if [ ! -d $HLT_DIR ]; then
	echo "No $HLT_DIR directory"
	exit 3
fi

#
# get the version we're working on
#

if [ "$cleanup_version" != "" ]; then
	Version=$cleanup_version
elif [ "$submit_version" != "" ]; then
	Version=$submit_version
else
	Version=$(cat ./version.txt)
	echo "Incrementing version ..."
	Version=$(expr $Version + 1)
	echo "Incrementing version ... done."
fi

# Incrementing version and update version dependent vars
MyBot_VFileName="MyBot.v$Version.py"
ARCHIVE_NAME="MyBot.v$Version.zip"

#
# if we're cleaning up, the do it + exit
#
if [ "$cleanup_version" != "" ]; then
	rm -fv $BOT_DIR/$MyBot_VFileName
	rm -fv $ARCHIVE_DIR/$ARCHIVE_NAME
	./manager.py -D MyBot.v$Version
	echo "Don't forget to manually update version.txt"
	exit 0
fi

#
# create new archive
#

echo "Zipping ..."

if [ -z $ARCHIVE_DIR/$ARCHIVE_NAME ]; then
	echo "Archive $ARCHIVE_DIR/$ARCHIVE_NAME already exists"
	exit 4
fi

/usr/bin/zip -r $ARCHIVE_NAME $MYBOT_FILE $VERSION_FILE install.sh $HLT_DIR $UTIL_DIR -x $EXCLUDES
Retval=$?

if [ $Retval != 0 ]; then
	echo "Error - zip failed with error $Retval"
	exit 5
fi

echo "Zipping ... done."

echo "Uploading ..."

if [ "$SUBMIT" == "1" ]; then
	python3 -m hlt_client bot -b $ARCHIVE_NAME upload
	Retval=$?

	if [ $Retval != 0 ]; then
		echo "Error - submit failed with error $Retval"
		exit 5
	fi
else
	echo "Skipping upload SUBMIT=$SUBMIT."
fi

echo "Uploading ... done."

#
# save current bot for testing
#

if [ -f $BOT_DIR/$MyBot_VFileName ]; then
	echo "Saved bot file $BOT_DIR/$MyBot_VFileName already exists"
	exit 6
fi

cp -f $MYBOT_FILE $BOT_DIR/$MyBot_VFileName
Retval=$?
if [ $Retval != 0 ]; then
	echo "Error - Copy of current bot failed with error $Retval"
	exit 7
fi

#
# Add current bot to the manager
#

if [ -f manager.py ]; then
	if [ -f $BOT_DIR/$MyBot_VFileName ]; then
		# use relative path ... easier to read
		./manager.py -A MyBot.v$Version -p "python3 bots/$MyBot_VFileName"
		./manager.py -a MyBot.v$Version
	else
		echo "Couldn't find $BOT_DIR/$MyBot_VFileName."
	fi
fi

#
# save the zip
#
mv -f $ARCHIVE_NAME $ARCHIVE_DIR
Retval=$?
if [ $Retval != 0 ]; then
	echo "WARNING - Move of the archive failed with error $Retval"
fi


# tag the version ... maybe wait and see if it compiles in official environment?
#git tag v$Version

echo "Uploading ... done."

echo "Updating version file ..."

echo $Version > $VERSION_FILE

echo "Updating version file ... done."

echo "Done."


