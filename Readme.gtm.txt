#
#
#

Repos
===============================

# Alternative visualizer (very useful)
https://github.com/fohristiwhirl/fluorine

# run matches between bots to compare different version (very useful)
https://gitlab.com/smiley1983/halite3-match-manager

# command line tool for interacting with halite.io, e.g. upload a bot, download game (optional)
https://github.com/HaliteChallenge/Halite-III/tree/master/tools/hlt_client

# halite server (optional)
https://github.com/HaliteChallenge/Halite-III

# reloader script ... parses .hlt files and feeds output to bot to produce a replay (optional)
https://github.com/fohristiwhirl/halite3_reload


Custom Tools
===============================

show-manager-results.py
----
Slightly modifed version of the match manager. Mods include 1) really not writing log files to disk. 2) The ability to execute a shell call (script) after each match  


show-map.py
----
Visualize a map of values. Useful to validate the custom cell values assigned for destination cell selection


show-metrics.py
----
Parse the generated metrics files and visualize them - very useful. Primary way to eval a match.


check-setting.sh bot1 bot2 ...
----
grep for settings strings for specified bots. This is useful for quickly checking configs before starting long running tests


cleanup.sh
----
Delete the many log replay files in one shot


follow-ship.sh
----
grep the log for key log messages that give an overview of a ships lifetime


make-candidate.sh
----
Take a snapshot of the current bot. Useful for creating test candidates. Also automatically adds snapshot to the test match manager


quick-parse-log.sh
----
grep out interesting log messages ... e.g. all errors/warnings, messages specific to a development feature etc. Good to habitually run to catch errors/warnings


rename-stats.sh
----
older versions have stats with different names. Attempt (not sure it work correctly) rename them so old/new bots can be compared.


run-fluorine.sh
----
Run the flourine view. If no file is provides, automatically used the more recent hlt file


save-bot.sh
----
copy the bot-0 log file to the logs directly. Uses as an arg to the modified match manager to save off log files after each match. See -x for the modified match manager.


show-data.sh
---
Very basic (you cut/paste data directly into the script) script to use matplotlib to visualize data.


submit.sh
----
Package up the current bot for submission. Relies uncessariy on version.txt.  Actual submission isn't working so I ended using the web submission method.






