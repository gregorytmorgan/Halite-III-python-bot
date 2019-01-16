#!/usr/bin/env python3
# Python 3.6
#
# 4 most recent stats for bot 0
# ./graph-game-metrics.py $(ls -tr -1 stats/*-bot-0.txt | tail -n 4)
#
# Profit stats for both bot-0 and bot-1
# ./graph-game-metrics.py $(ls -rt -1 stats/profit-*-bot-?.txt | tail -n 2)
#
# Two stats for two competitors
# ./graph-game-metrics.py $(ls -rt -1 stats/{mined,profit}-*-bot-?.txt | tail -n 4)
#

#import math
#from scipy.stats import norm
from scipy.optimize import curve_fit
import numpy as np
import matplotlib.pyplot as plt
import sys
import getopt
import re
import os

try:
   opts, args = getopt.getopt(sys.argv[1:] , "hvt:", ["help", "verbose", "title"])
except getopt.GetoptError:
   print(sys.argv[0])
   sys.exit(2)

def usage():
    program_name = sys.argv[0]
    print("Usage: {} [options] files".format(program_name))
    print("-h\tHelp.")
    print("-v\tVerbose.")
    print("\nExamples:")
    print("Mining rate for bot 0 for the last 4 games:")
    print("./show-metrics.py $(ls -tr -1 stats/mining_rate-*-bot-0.log | tail -n 4)")
    print("")
    print("Profit stats for both bot-0 and bot-1:")
    print("./show-metrics.py $(ls -rt -1 stats/profit-*-bot-?.log | tail -n 2)")
    print("")
    print("Three stats for both bot-0 and bot-1:")
    print("./show-metrics.py $(ls -rt -1 stats/{mined,profit,mining_rate}-*-bot-?.log | tail -n 6)")
    print("")
    print("Ships v Mining_rate stats for both bot-0 and bot-1:")
    print("./show-metrics.py $(ls -rt -1 stats/{mined,profit,mining_rate,ship_count}-*-bot-?.log | tail -n 8)")
    print("")
    print("[1] Make sure the tail count = number of players * number of stats")

def running_mean(x, N):
    cumsum = np.cumsum(np.insert(x, 0, 0))
    return (cumsum[N:] - cumsum[:-N]) / float(N)

def main():
    X = []
    Y = []
    data = []
    file_names = []
    verbose = False
    title = ""
    trendline = False

    for o, a in opts:
        if o == "-v":
            verbose = True
        elif o in ("-t", "--title"):
            title = a
        elif o in ("-h", "--help"):
            usage()
            sys.exit(0)
        else:
            assert False, "unhandled option"

    for f in args:
        file_names.append(f)

    #total = 0
    #symbols = [',', '.', '^', '*', '+', 'x']
    #sym_idx = 0
    #linestyles = ['-', '--', '-.', ':']
    line_colors = ["g", "b", "r", "c", "m", "y", "k", "w"]

    fig, ax1 = plt.subplots()

    ax1.yaxis.tick_right()
    ax1.yaxis.set_visible(False)

    #fig = plt.figure(frameon=False)
    fig.set_size_inches(12, 9)

    #ax1 = plt.gca()

    ax2 = ax1.twinx()
    ax2.yaxis.set_visible(False)

    # push all the output down a line for cosmetics
    if verbose:
        print("")

    known_metrics = {
        "assn_drop_amount": {},
        "assn_duration": {"cumulative":False, "window_size": 70},
        "assn_duration2": {},
        "assn_explore_duration": {},
        "assn_point_distance": {},
        "assn_transit_duration":  {"cumulative":False, "window_size": 70, "key":-2},
        "burned": {},
        "gathered": {},
        "loiter_distances": {"cumulative":False},
        "loiter_multiples": {},
        "loiter_offsets": {},
        "mined": {},
        "mining_rate": {"cumulative":False},
        "profit": {},
        "raw_loiter_points": {},
        "ship_count": {"cumulative":False},
        "spend": {},
        "turn_time": {"cumulative":False}
    }

    #re_metrics = "trip_data|burned|mined|mining_rate|ship_count|gathered|profit|spent|loiter_distances|return_duration|trip_transit_duration"

    re_metrics = "|".join(known_metrics.keys())

    window_data = []

    default_symbol = "," # pixel
    default_step = 1
    default_cumulative = True
    default_key = -1
    default_window_size = 0

    for fname in file_names:
        X.clear()
        Y.clear()
        data.clear()
        val = 0
        line_no = 0

        if verbose:
            print("Processing {}".format(fname))

        m = re.search(r"^(" + re_metrics + ")-([0-9]+)-([0-9]+)-bot-([0-9])", os.path.basename(fname))

        if m is None:
            print("Unknown metric: {}".format(fname))
            exit(1)
        else:
            metric = m.group(1)
            bot = m.group(4)

        data_label = metric.title() + " bot-" + bot
        bot_color = line_colors[(int(bot)) % len(line_colors)]

        #
        # setup plot attribs
        #

        if "window_size" in known_metrics[metric]:
            window_size = known_metrics[metric]["window_size"]
        else:
            window_size = default_window_size

        if "symbol" in known_metrics[metric]:
            symbol = known_metrics[metric]["symbol"]
        else:
            symbol = default_symbol

        if "key" in known_metrics[metric]:
            key = known_metrics[metric]["key"]
        else:
            key = default_key

        if "step" in known_metrics[metric]:
            step = known_metrics[metric]["step"]
        else:
            step = default_step

        if "cumulative" in known_metrics[metric]:
            cumulative = known_metrics[metric]["cumulative"]
        else:
            cumulative = default_cumulative

        #
        # plot each metric/file
        #
        with open(fname, "r") as file:
          for line in file:
            line_no += 1
            line = line.strip()
            if not re.match(r"^\(", line):
                continue

            item = eval(line)

            if cumulative:
                val += item[key]
            elif window_size:
                window_data = np.append(window_data, item[key])
                val = np.mean(window_data[-window_size:])
            else:
                val = item[key]

            if line_no % step == 0:
                X.append(item[0])
                Y.append(val)

        #plt.scatter(X, Y, label=data_label, marker = symbol) # symbols[sym_idx % 3]
        if len(X):
            if cumulative:
                ax1.yaxis.tick_right()
                ax1.yaxis.set_visible(True)
                ax1.plot(X, Y, label = data_label, marker = symbol, color = bot_color)
            elif window_size:
                ax2.yaxis.tick_left()
                ax2.yaxis.set_visible(True)
                ax2.plot(X, Y, label = data_label, marker = symbol, color = bot_color)
            else:
                # plot non cumulative data. E.g. mining_rate, ...
                ax2.yaxis.tick_left()
                ax2.yaxis.set_visible(True)
                ax2.plot(X, Y, label = data_label, marker = symbol, color = bot_color)

                if trendline:
                    def fexp(x, a, b , c):
                        return a * np.exp(-b * x) + c

                    def flinear():
                        return a+b*x

                    n = len(X) # n == the number of data points to use

                    fxn = np.linspace(1, X[:n][-1])
                    try:
                        popt, pcov = curve_fit(fexp, X[:n], Y[:n], p0=[float(X[0]), 0.01, 1.], bounds=[0., [800., .2, 4.]])
                        plt.plot(fxn, fexp(fxn, *popt), label="fexp", marker = ",")
                    except:
                        popt, pcov = curve_fit(flinear, X[:n], Y[:n], p0=[float(X[0]), -4], bounds=[0., [800., -100.]])
                        plt.plot(fxn, flinear(fxn, *popt), label="ff", marker = "+")

    if file_names and len(X):
        handles, labels = ax1.get_legend_handles_labels()
        if handles:
            labels, handles = zip(*sorted(zip(labels, handles), key=lambda t: t[0])) # sort both labels and handles by labels
            ax1.legend(handles, labels, loc='upper right')

        handles2, labels2 = ax2.get_legend_handles_labels()
        if handles2:
            labels2, handles2 = zip(*sorted(zip(labels2, handles2), key=lambda t: t[0])) # sort both labels and handles by labels
            ax2.legend(handles2, labels2, loc='upper left')

        if m is None:
            plt.gca().set_title("{}-{} {}".format("Unknown", "Unknown", title))
        else:
            plt.gca().set_title("{}-{} {}".format(m.group(2), m.group(3), title))

        fig.tight_layout()

        plt.show()
    else:
        print("No data.")
        exit(1)

if __name__ == "__main__":
    main()