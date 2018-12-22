#!/usr/bin/env python3
# Python 3.6

#import math
#from scipy.stats import norm
#import numpy as np
import matplotlib.pyplot as plt
import sys
import getopt
import re

try:
   opts, args = getopt.getopt(sys.argv[1:] , "hv", ["help", "verbose"])
except getopt.GetoptError:
   print(sys.argv[0])
   sys.exit(2)


def usage():
    program_name = sys.argv[0]
    print("Usage: {} [options] [files]".format(program_name))
    print("-h\tHelp.")
    print("-v\tVerbose.")
    print("\nExample:")
    print("Either provide a file name on the command line, or stdin")


def main():
    data = []
    file_names = []
    verbose = False

    for o, a in opts:
        if o == "-v":
            verbose = True
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"

    if len(args) == 0:
        file_names = False
    else:
        for f in args:
            file_names.append(f)

    if file_names is False:
        data = dummy_data # REPLACE ME
    else:
        for fname in file_names:
            line_no = 0
            if verbose: print("Processing {}".format(fname))

            players = {}

            with open(fname, "r") as file:
                for line in file:
                    line_no += 1
                    line = line.strip()

                    if not re.match(r"^\(", line):
                        continue

                    match_data = eval(line)

                    match_players = match_data[1].split(',')
                    match_results = match_data[2].split(',')

                    for mp in match_players:
                        if mp not in players:
                            players[mp] = {
                                "wins": {},
                                "loses": {}
                            }

                    winner = None
                    losers = []
                    for player, rank in zip(match_players, match_results):
                        if int(rank) == 1:
                            winner = player
                        else:
                            losers.append(player)

                    for loser in losers:
                        if loser in players[winner]["wins"]:
                            players[winner]["wins"][loser] += 1
                        else:
                            players[winner]["wins"][loser] = 1

                        if winner in players[loser]["loses"]:
                            players[loser]["loses"][winner] += 1
                        else:
                            players[loser]["loses"][winner] = 1

#                    print("player {} defeated {}".format(winner, ", ".join(losers)))

#            print("{}".format(players))

            output = []

            results = [["x" for _ in range(len(players) + 1)] for _ in range(len(players) + 1)]

            row = 0
            col = 0

            max_player_length = 12
            sep = ".."

            results[row][col] = "\t\t"
            col += 1

            for player in players:
                output.append("{}".format(player))

                if len(player) > max_player_length:
                    player_name = player[0:round(max_player_length / 2) - len(sep)] + sep + player[-round(max_player_length / 2) - len(sep):]
                else:
                    player_name = player

                results[row][col] = player_name
                col += 1

            row += 1

            for player1, p1_data in players.items():

                col = 0

                results[row][col] = player1

                for player2, p2_data in players.items():

                    col += 1

                    output.append(player1)

                    if player1 == player2:
                        wins = "-"
                        loses = "-"
                    else:
                        if player2 in players[player1]["wins"]:
                            output.append("wins {} v {}: {}".format(player1, player2, players[player1]["wins"][player2]))
                            wins = players[player1]["wins"][player2]
                        else:
                            wins = 0

                        if player2 in players[player1]["loses"]:
                            loses = str(players[player1]["loses"][player2])
                        else:
                            loses = 0

                    results[row][col] =  "{}/{}".format(wins, loses)

                row += 1

            for r in results:
                if r[0].strip() == "":
                    print("\t".join(r))
                else:
                    print("\t\t".join(r))

    if (verbose):
        print("Done")

if __name__ == "__main__":
    main()
