#!/bin/bash

cnt=$(rm -vf stats/*.log | wc -l)
echo "Cleaned up $cnt log files in /stats."

cnt=$(rm -vf stats/*.txt | wc -l)
echo "Cleaned up $cnt txt files in /stats."

cnt=$(rm -vf replays/*.log | wc -l)
echo "Cleaned up $cnt log files in /replays."

cnt=$(rm -vf replays/*.hlt | wc -l)
echo "Cleaned up $cnt txt files in /replays."

cnt=$(rm -vf error_replays/*.log | wc -l)
echo "Cleaned up $cnt log files in /error_replays."

cnt=$(rm -vf error_replays/*.hlt | wc -l)
echo "Cleaned up $cnt hlt files in /error_replays."

if [ -d logs ]; then
	cnt=$(rm -vf logs/* | wc -l)
	echo "Cleaned up $cnt in /logs."
fi

echo "Done."
