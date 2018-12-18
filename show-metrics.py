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
#import numpy as np
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
    print("4 most recent stats for bot 0 [1]:")
    print("./show-metrics.py $(ls -tr -1 stats/*-bot-0.log | tail -n 4)")
    print("")
    print("Profit stats for both bot-0 and bot-1 [1]:")
    print("./show-metrics.py $(ls -rt -1 stats/profit-*-bot-?.log | tail -n 2)")
    print("")
    print("Two stats for both bot-0 and bot-1 [1]:")
    print("./show-metrics.py $(ls -rt -1 stats/{mined,profit}-*-bot-?.log | tail -n 4)")
    print("")
    print("[1] Make sure the tail count = number of players * number of stats")

def main():
    X = []
    Y = []
    data = []
    file_names = []
    verbose = False
    title = ""

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

    fig = plt.figure(frameon=False)
    fig.set_size_inches(8, 6)

    for fname in file_names:
        X.clear()
        Y.clear()
        data.clear()
        val = 0
        line_no = 0

        if verbose:
            print("Processing {}".format(fname))

        metrics = "burned|mined|gathered|profit|spent|loiter_distances|return_duration"
        m = re.search(r"^(" + metrics + ")-([0-9]+)-([0-9]+)-bot-([0-9])", os.path.basename(fname))

        if m is None:
            metric = "Unknown"
            bot = "Unknown"
        else:
            metric = m.group(1)
            bot = m.group(4)

        data_label = metric.title() + " bot-" + bot
        cumulative = True # many stats are cumulative

        if metric == "gathered":
            step = 1
            symbol = '.'
        elif metric == "burned":
            step = 50
            symbol = '.'
        elif metric == "mined":
            step = 1
            symbol = '.'
        elif metric == "profit":
            step = 5
            symbol = '.'
        elif metric == "spent":
            step = 5
            symbol = '.'
        elif metric == "return_duration":
            step = 1
            symbol = '.'
        elif metric == "loiter_distances":
            step = 1
            symbol = '.'
            cumulative = False
        else:
            symbol = '.'
            step = 1

        with open(fname, "r") as file:
          for line in file:
            line_no += 1
            item = eval(line.strip())
            if cumulative:
                val += item[len(item) - 1]
            else:
                val = item[len(item) - 1]

            if line_no % step == 0:
                X.append(item[0])
                Y.append(val)

        #plt.scatter(X, Y, label=data_label, marker = symbol) # symbols[sym_idx % 3]
        plt.plot(X, Y, label=data_label, marker = symbol) # symbols[sym_idx % 3]
        #plt.plot(X, Y, scalex=False, scaley=False, marker='+') # no auto scale

    if file_names:
        ax = plt.gca()
        handles, labels = ax.get_legend_handles_labels()
        labels, handles = zip(*sorted(zip(labels, handles), key=lambda t: t[0])) # sort both labels and handles by labels
        plt.legend(handles, labels, loc='upper left')
        plt.gca().set_title("{}-{} {}".format(m.group(2), m.group(3), title))
        plt.show()
    else:
        print("No data.")
        exit(1)

if __name__ == "__main__":
    main()