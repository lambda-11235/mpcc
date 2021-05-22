#!/usr/bin/env python3

import argparse
import numpy as np

import matplotlib
import matplotlib as mpl
import matplotlib.pyplot as plt

from data import Data

bwctlStartTime = 0

parser = argparse.ArgumentParser(description="Plots test results.")
parser.add_argument('test', type=str, nargs="+",
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
parser.add_argument('--rate-range', type=float, nargs=2,
        help="Range in rates on x axis.")
parser.add_argument('--rtt-range', type=float, nargs=2,
        help="Range in RTTs on x axis.")
args = parser.parse_args()


data = []
for t in args.test:
    data.append(Data(t))

streams = [d.streams[args.stream] for d in data]

modules = []
for i, stream in enumerate(streams):
    sk = stream.socket.mode()[0]
    c = data[i].connections.query("socket == @sk")

    if args.all_modules:
        modules.append(data[i].module)
    elif args.with_id is not None:
        q = 'id == "' + str(args.with_id) + '"'
        modules.append(data[i].module.query(q))
    else:
        lport = c.local_port.iloc[0]
        q = 'lport == ' + str(lport)
        modules.append(data[i].module.query(q))

for stream in streams:
    stream.sort_values('start', inplace=True)

for i, module in enumerate(modules):
    modules[i] = module.sort_values('time')#, inplace=True)

titles = []
for i, t in enumerate(args.test):
    if args.title is not None and i < len(args.title):
        titles.append(args.title[i])
    else:
        titles.append(t)


mpl.style.use('seaborn-bright')
mpl.rc('figure', dpi=200)


def ecdfPlotData(xs):
    xs = sorted(xs)
    ys = [(i + 1)/len(xs) for i in range(len(xs))]
    return xs, ys

def setXTicks(ax, start, stop):
    tick = 10**np.ceil(np.log10((stop - start)/10))

    ax.set_xticks(np.arange(start, stop, tick/4), minor=True)
    ax.set_xticks(np.arange(start, stop, tick))


### Rate ###
fig = plt.figure()
ax = fig.add_subplot(111)

for i, stream in enumerate(streams):
    xs, ys = ecdfPlotData(stream.bits_per_second/2**20)
    ax.plot(xs, ys, ds='steps-post', label=titles[i])

ax.set_xlabel("r (Mbps)")
ax.set_ylabel("P(Rate < r)")
ax.legend()

ax.set_yticks(np.arange(0, 1.01, 0.1))

if args.rate_range is not None:
    setXTicks(ax, args.rate_range[0], args.rate_range[1])

ax.grid(b=True, which='both')

if args.rate_range is not None:
    ax.set_xlim(args.rate_range[0], args.rate_range[1])

if args.output is not None:
    fig.savefig(args.output + "-rate-ecdf." + args.output_extension, bbox_inches='tight')


### RTT ###
fig = plt.figure()
ax = fig.add_subplot(111)

for i, stream in enumerate(streams):
    xs, ys = ecdfPlotData(stream.rtt/1000)
    ax.plot(xs, ys, ds='steps-post', label=titles[i])

ax.set_xlabel("t (ms)")
ax.set_ylabel("P(RTT < t)")
ax.legend()

ax.set_yticks(np.arange(0, 1.01, 0.1))

if args.rtt_range is not None:
    setXTicks(ax, args.rtt_range[0], args.rtt_range[1])

ax.grid(b=True, which='both')

if args.rtt_range is not None:
    ax.set_xlim(args.rtt_range[0], args.rtt_range[1])

if args.output is not None:
    fig.savefig(args.output + "-rtt-ecdf." + args.output_extension, bbox_inches='tight')


if args.output is None:
    plt.show()
