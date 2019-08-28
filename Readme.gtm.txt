#
# https://halite.io
#
# https://2018.halite.io
#


Repos
=========================================

# Alternative visualizer
https://github.com/fohristiwhirl/fluorine

# run matches between bots to compare different version - useful
https://gitlab.com/smiley1983/halite3-match-manager

# command line tool for interacting with halite.io, e.g. upload a bot, download game
https://github.com/HaliteChallenge/Halite-III/tree/master/tools/hlt_client

# totally optional
https://github.com/HaliteChallenge/Halite-III


Running the Game
=========================================

> ./run_game.sh
[info] Map seed is 1567005861
[info] [P0] Launching with command python3 MyBot.py
[info] [P1] Launching with command python3 MyBot.py
[info] [P0] Initializing player
[info] [P1] Initializing player
[info] [P0] Initialized player MyBot.v28
[info] [P1] Initialized player MyBot.v28
[info] Player initialization complete
...


Viewing the Game Output
=========================================

> ./run_fluorine.sh

[A UI window will open. Space bar starts/stops autoplay. Left/right arrows for single move]


Notes
=========================================

Ship states and navigation
-----------------------------------------

Exploring
1. Exploring ships have two 'sub-states', 'navigating' and 'mining/searching'. Not implemented.

2. Performance, per the discussion linked below, 'inspiration' is expensive. You can
   test without it by using a custom config. 'halite-config.json'.
   https://forums.halite.io/t/solved-halite-cli-cpu-usage/716/6

