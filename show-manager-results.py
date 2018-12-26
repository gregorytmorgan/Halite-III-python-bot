#!/usr/bin/env python3
# Python 3.6

#import math
#from scipy.stats import norm
#import numpy as np
import matplotlib.pyplot as plt
import sys
import getopt
import re

global consider_rank
global verbose
global sep
global max_player_length

verbose = False
consider_rank = False
max_player_length = 12
sep = ".."

try:
   opts, args = getopt.getopt(sys.argv[1:] , "hrv", ["help", "rank", "verbose"])
except getopt.GetoptError:
   print(sys.argv[0])
   sys.exit(2)

def usage():
    program_name = sys.argv[0]
    print("Usage: {} [options] files|STDIN".format(program_name))
    print("-h\tHelp.")
    print("-r\tConsider rank - e.g. In a 4p match 3rd gets 1 win 2 loses, otherwise the only the winner get a win.")
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

        if consider_rank:
            for player, rank in zip(match_players, match_results):
                for player2, rank2 in zip(match_players, match_results):
                    if player == player2:
                        continue

                    if rank > rank2:
                        players[player]["wins"][player2] = players[player]["wins"][player2] + 1 if player2 in players[player]["wins"] else 1
                    else:
                        players[player]["loses"][player2] = players[player]["loses"][player2] + 1 if player2 in players[player]["loses"] else 1
        else:
            losers = []
            winner = None

            # seperate in winner and losers only
            for player, rank in zip(match_players, match_results):
                if int(rank) == 1:
                    winner = player
                else:
                    losers.append(player)

            for loser in losers:
                players[winner]["wins"][loser] = players[winner]["wins"][loser] + 1 if loser in players[winner]["wins"] else 1
                players[loser]["loses"][winner] = players[loser]["loses"][winner] + 1 if winner in players[loser]["loses"] else 1

    return players


def print_win_lose_table(wins_lose_data):
    row = 0
    col = 0
    results = [["x" for _ in range(len(wins_lose_data) + 1)] for _ in range(len(wins_lose_data) + 1)]

    results[row][col] = "\t\t"
    summary_results = []
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
        total_wins = 0
        total_loses = 0
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
            total_wins += int(wins) if wins != "-" else 0
            total_loses += int(loses)  if loses != "-" else 0

        row += 1

        summary_results.append((player1, total_wins, total_loses))

    for r in results:
        if r[0].strip() == "":
            print("\t".join(r))
        else:
            print("\t\t".join(r))

    summary_results.sort(key=lambda item: item[1]/(item[1] + item[2]), reverse=True) #

    print("\n")

    for r in summary_results:
        print("{}\t{}/{} {}%".format(r[0], r[1], r[2], round(r[1]/(r[1] + r[2]) * 100, 0)))


def main():
    global verbose
    global consider_rank
    lines = []
    file_names = []

    for o, a in opts:
        if o in ("-r", "--rank"):
            consider_rank = True
        elif o in ("-v", "--verbose"):
            verbose = True
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"

    if verbose:
        print("verbose:" + str(verbose))
        print("consider_rank:" + str(consider_rank))

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
