#!/usr/bin/env python3
# Python 3.6

#import math
#from scipy.stats import norm
#import numpy as np
import matplotlib.pyplot as plt
import sys
import getopt
import re

global verbose
global sep
global max_player_length

verbose = False
max_player_length = 12
sep = ".."


try:
   opts, args = getopt.getopt(sys.argv[1:] , "hv", ["help", "verbose"])
except getopt.GetoptError:
   print(sys.argv[0])
   sys.exit(2)


def usage():
    program_name = sys.argv[0]
    print("Usage: {} [options] files|STDIN".format(program_name))
    print("-h\tHelp.")
    print("-v\tVerbose.")
    print("Example: ./manager.py -R 0 | ./show-manager-results.py")


def parse_lines(lines):
    players = {}
    for line in lines:
        match_data = eval(line)
        match_players = match_data[1].split(',')
        match_results = match_data[2].split(',')

        for mp in match_players:
            if mp not in players:
                players[mp] = {"wins": {},"loses": {}}

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

    return players

def print_win_lose_table(wins_lose_data):
    row = 0
    col = 0
    results = [["x" for _ in range(len(wins_lose_data) + 1)] for _ in range(len(wins_lose_data) + 1)]

    results[row][col] = "\t\t"
    col += 1

    for player in wins_lose_data:
        if len(player) > max_player_length:
            player_name = player[0:round(max_player_length / 2) - len(sep)] + sep + player[-round(max_player_length / 2) - len(sep):]
        else:
            player_name = player

        results[row][col] = player_name
        col += 1

    row += 1

    for player1, p1_data in wins_lose_data.items():
        col = 0
        results[row][col] = player1
        for player2, p2_data in wins_lose_data.items():
            col += 1
            if player1 == player2:
                wins = "-"
                loses = "-"
            else:
                if player2 in wins_lose_data[player1]["wins"]:
                    #output.append("wins {} v {}: {}".format(player1, player2, wins_lose_data[player1]["wins"][player2]))
                    wins = wins_lose_data[player1]["wins"][player2]
                else:
                    wins = 0

                if player2 in wins_lose_data[player1]["loses"]:
                    loses = str(wins_lose_data[player1]["loses"][player2])
                else:
                    loses = 0

            results[row][col] =  "{}/{}".format(wins, loses)

        row += 1

    for r in results:
        if r[0].strip() == "":
            print("\t".join(r))
        else:
            print("\t\t".join(r))

def main():
    global verbose
    lines = []
    file_names = []

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

    if not file_names:
        if verbose: print("Processing {}".format("STDIN"))
        for line in sys.stdin:
            line = line.strip()
            if not re.match(r"^\(", line):
                continue

            lines.append(line)
    else:
        for fname in file_names:
            if verbose: print("Processing {}".format(fname))
            with open(fname, "r") as file:
                for line in file:
                    line = line.strip()
                    if not re.match(r"^\(", line):
                        continue

                    lines.append(line)

    wins_lose_data = parse_lines(lines)

    print_win_lose_table(wins_lose_data)

    if (verbose):
        print("Done")

if __name__ == "__main__":
    main()
