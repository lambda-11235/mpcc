#!/usr/bin/env python3

import argparse
import numpy as np

import matplotlib
import matplotlib as mpl
import matplotlib.pyplot as plt

from data import Data

bwctlStartTime = 0

parser = argparse.ArgumentParser(description="Plots test results.")
parser.add_argument('test', type=str, nargs='+',
        help="The name of the test to plot.")
parser.add_argument('-o', '--output', type=str,
        help="Sets output file base name.")
parser.add_argument('-e', '--output-extension', type=str, default="png",
        help="Sets the extension for output files (i.e. pdf, png, etc.).")
parser.add_argument('-t', '--title', type=str, nargs="*",
        help="Title for each test.")
parser.add_argument('-s', '--stream', type=int, default=0,
        help="Select the iperf stream to use.")
parser.add_argument('-a', '--all-modules', action='store_true',
        help="Plot all module data.")
parser.add_argument('-i', '--with-id', type=int, default=None,
        help="Plot all module data with a certain id.")
parser.add_argument('--time-range', type=float, nargs=2,
        help="Range for y axis.")
parser.add_argument('--rate-range', type=float, nargs=2,
        help="Range in rates on x axis.")
parser.add_argument('--rtt-range', type=float, nargs=2,
        help="Range in RTTs on x axis.")
parser.add_argument('-f', '--font-size', type=int, default=32,
        help="Sets font size.")
args = parser.parse_args()


mpl.style.use('seaborn-bright')
mpl.rc('figure', dpi=200)

#if args.output is not None:
#    matplotlib.rc('font', size=args.font_size)


streams = []
titles = []
for i, t in enumerate(args.test):
    streams.append(Data(t).streams[args.stream])

    if args.title is not None and i < len(args.title):
        titles.append(args.title[i])
    else:
        titles.append(t)

### Rate ###
fig = plt.figure()
ax = fig.add_subplot(111)

for stream, title in zip(streams, titles):
    ax.plot(stream.start, stream.bits_per_second/2**20, label=title)

ax.set_xlabel("time (s)")
ax.set_ylabel("Rate (Mbps)")
ax.legend()
ax.grid(b=True, which='major')

if args.time_range is not None:
    ax.set_xlim(args.time_range[0], args.time_range[1])

if args.rate_range is not None:
    ax.set_ylim(args.rate_range[0], args.rate_range[1])

if args.output is not None:
    fig.savefig(args.output + "-rate." + args.output_extension, bbox_inches='tight')


### RTT ###
fig = plt.figure()
ax = fig.add_subplot(111)

for stream, title in zip(streams, titles):
    ax.plot(stream.start, stream.rtt/1000, label=title)

ax.set_xlabel("time (s)")
ax.set_ylabel("RTT (ms)")
ax.legend()
ax.grid(b=True, which='major')

if args.time_range is not None:
    ax.set_xlim(args.time_range[0], args.time_range[1])

if args.rtt_range is not None:
    ax.set_ylim(args.rtt_range[0], args.rtt_range[1])

if args.output is not None:
    fig.savefig(args.output + "-rtt." + args.output_extension, bbox_inches='tight')


if args.output is None:
    plt.show()
