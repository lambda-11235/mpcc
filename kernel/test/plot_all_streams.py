#!/usr/bin/env python3

import argparse
import numpy as np

import matplotlib
import matplotlib as mpl
import matplotlib.pyplot as plt

from data import Data

bwctlStartTime = 0

parser = argparse.ArgumentParser(description="Plots test results.")
parser.add_argument('test', type=str,
        help="The name of the test to plot.")
parser.add_argument('-o', '--output', type=str,
        help="Sets output file base name.")
parser.add_argument('-e', '--output-extension', type=str, default="png",
        help="Sets the extension for output files (i.e. pdf, png, etc.).")
parser.add_argument('--time-range', type=float, nargs=2,
        help="Range for y axis.")
parser.add_argument('--rate-range', type=float, nargs=2,
        help="Range in rates on x axis.")
parser.add_argument('--rtt-range', type=float, nargs=2,
        help="Range in RTTs on x axis.")
args = parser.parse_args()


mpl.style.use('seaborn-bright')
mpl.rc('figure', dpi=200)

data = Data(args.test)

### Rate ###
fig = plt.figure()
ax = fig.add_subplot(111)

sumStart = 0
sumBPS = 0
for i, stream in enumerate(data.streams):
    sumStart = stream.start
    sumBPS += stream.bits_per_second
    ax.plot(stream.start, stream.bits_per_second/2**20, label=f"Flow {i+1}")
    
ax.plot(sumStart, sumBPS/2**20, label="Sum of Flows")

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

sumStart = 0
sumBPS = 0
for i, stream in enumerate(data.streams):
    sumStart = stream.start
    sumBPS += stream.bits_per_second
    ax.plot(stream.start, stream.rtt/1000, label=f"Flow {i+1}")

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

### Jain ###

fig = plt.figure()
ax = fig.add_subplot(111)

bps = [s.bits_per_second for s in data.streams]
sum_ = sum(bps)
sumSqr = sum([b*b for b in bps])
jain = sum_**2/(len(bps)*sumSqr)

ax.plot(sumStart, jain)

ax.set_xlabel("time (s)")
ax.set_ylabel("Jain Index")
ax.grid(b=True, which='major')

if args.time_range is not None:
    ax.set_xlim(args.time_range[0], args.time_range[1])

if args.output is not None:
    fig.savefig(args.output + "-jain." + args.output_extension, bbox_inches='tight')

### Jain eCDF ###

fig = plt.figure()
ax = fig.add_subplot(111)

jain = np.sort(jain)
cdf = np.arange(1, len(jain)+1)/len(jain)

ax.plot(jain, cdf)

ax.set_xlabel("j")
ax.set_ylabel("P(Jain Index < j)")
ax.grid(b=True, which='major')

if args.output is not None:
    fig.savefig(args.output + "-jain-ecdf." + args.output_extension, bbox_inches='tight')



if args.output is None:
    plt.show()
