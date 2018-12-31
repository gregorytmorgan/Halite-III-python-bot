#!/usr/bin/env python3
# Python 3.6

#import math
#from scipy.stats import norm
#import numpy as np
import sys
import getopt
import re

global consider_rank
global verbose
global map_size
global player_count
global sep
global max_player_length

verbose = 0
consider_rank = False
map_size = []
player_count = 0
max_player_length = 12
sep = ".."

try:
   opts, args = getopt.getopt(sys.argv[1:] , "hm:p:rv", ["help", "map_size", "player_count", "rank", "verbose"])
except getopt.GetoptError:
   print(sys.argv[0])
   sys.exit(2)

def usage():
    program_name = sys.argv[0]
    print("Usage: {} [options] files|STDIN".format(program_name))
    print("-h\tHelp.")
    print("-m\tMap sizes - Comma separated list of 32|40|48|56|64, default:any")
    print("-m\tPlayer count - 2|4, default:any")
    print("-r\tConsider rank - e.g. In a 4p match 3rd gets 1 win 2 loses, otherwise the only the winner get a win.")
    print("-v\tVerbose. Multiple, e.g. -vv yields more detail.")
    print("Example: ./manager.py -R 0 | ./show-manager-results.py")


def parse_lines(lines):
    players = {}
    match_count = 0
    for line in lines:
        match_data = eval(line)
        match_players = match_data[1].split(',')
        match_results = match_data[2].split(',')
        match_map_size = int(match_data[3])
        match_player_count = len(match_players)

        if map_size and match_map_size not in map_size:
            continue

        if player_count and match_player_count != player_count:
            continue

        match_count += 1

        for mp in match_players:
            if mp not in players:
                players[mp] = {"wins": {},"loses": {}}

        for player, rank in zip(match_players, match_results):
            if rank == "1":
                if verbose > 1:
                    losers = match_players[:]
                    losers.remove(player)
                    losers.sort()
                    print("{} beats {}".format(player, losers))
                players[player]["wins"]["match"] = players[player]["wins"]["match"] + 1 if "match" in players[player]["wins"] else 1
            else:
                players[player]["loses"]["match"] = players[player]["loses"]["match"] + 1 if "match" in players[player]["loses"] else 1

            for player2, rank2 in zip(match_players, match_results):
                if player == player2:
                    continue

                if rank < rank2:
                    players[player]["wins"][player2] = players[player]["wins"][player2] + 1 if player2 in players[player]["wins"] else 1
                else:
                    players[player]["loses"][player2] = players[player]["loses"][player2] + 1 if player2 in players[player]["loses"] else 1

    return players, match_count


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
            wins = 0
            loses = 0
            if player1 != player2:
                if player2 in wins_lose_data[player1]["wins"]:
                    wins = int(wins_lose_data[player1]["wins"][player2])

                if player2 in wins_lose_data[player1]["loses"]:
                    loses = int(wins_lose_data[player1]["loses"][player2])

                if consider_rank:
                    total_wins += wins
                    total_loses += loses

            results[row][col] =  "{}/{}".format("-" if player1 == player2 else wins, "-" if player1 == player2 else loses)

        row += 1

        if consider_rank:
            summary_results.append((player1, total_wins, total_loses))
        else:
            total_wins =  wins_lose_data[player1]["wins"]["match"] if "match" in wins_lose_data[player1]["wins"] else 0
            total_loses = wins_lose_data[player1]["loses"]["match"] if "match" in wins_lose_data[player1]["loses"] else 0
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
    global map_size
    global player_count
    lines = []
    file_names = []

    for o, a in opts:
        if o in ("-r", "--rank"):
            consider_rank = True
        elif o in ("-m", "--map_size"):
            map_size = list(map(int, a.split(",")))
        elif o in ("-p", "--player_count"):
            player_count = int(a)
        elif o in ("-v", "--verbose"):
            verbose += 1
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"

    if verbose:
        print("consider_rank:" + str(consider_rank))
        print("map_size:" + str(map_size))
        print("player_count:" + str(player_count))
        print("verbose:" + str(verbose))

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

    wins_lose_data, match_count = parse_lines(lines)

    print("Read {} matches".format(match_count))

    print_win_lose_table(wins_lose_data)

    if (verbose):
        print("Done")

if __name__ == "__main__":
    main()
