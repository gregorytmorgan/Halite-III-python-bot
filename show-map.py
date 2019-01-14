#!/usr/bin/env python3
# Python 3.6

#
# simple script to plot map data
#

#import math
#from scipy.stats import norm
#import numpy as np
import matplotlib.pyplot as plt
import sys
import getopt

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
    print("")
    print("Either provide a file name on the command line, or edit the data variable in the source file")
    print("")
    print("\nExample - multiple files are displayed as below:")
    print("./show-map.py -v $(ls -rt1 stats/cell_value_map_turn_*-bot-0.log | tail -n 6)")

dummy_data = [[-399,-231,-371,-444,-276,-420],
    [-246,-100, 47, -182,-140,-261],
    [-236,-235,-241,-347,-405,-338],
    [-426,-364,-161,-261,-263,-407]]

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
        plt.imshow(data, cmap='hot', interpolation='nearest')
        plt.show()
    else:
        for fname in file_names:
            if verbose: print("Processing {}".format(fname))
            with open(fname, "r") as file:
                raw_data = file.read()
                data = eval(raw_data.strip())

            fig = plt.figure(frameon=False)
            fig.set_size_inches(9, 9)

            ax = plt.subplot(111, aspect = 'equal')
            
            plt.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)

            fig.tight_layout()

            plt.imshow(data, cmap='hot', interpolation='nearest')

            plt.show()

    if (verbose):
        print("Done")

if __name__ == "__main__":
    main()
