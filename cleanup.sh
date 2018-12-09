#!/bin/bash

cnt=$(rm -vf stats/*.log | wc -l)
echo "Cleaned up $cnt log files in stats."

cnt=$(rm -vf replays/*.log | wc -l)
echo "Cleaned up $cnt log files in replays."

cnt=$(rm -vf replays/*.hlt | wc -l)
echo "Cleaned up $cnt txt files in replays."

cnt=$(rm -vf error_replays/*.log | wc -l)
echo "Cleaned up $cnt log files in error_replays."

echo "Done."