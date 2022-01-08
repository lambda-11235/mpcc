#!/usr/bin/env python

import argparse
import json
import sys

import matplotlib
import matplotlib.pyplot as plt

import numpy as np
import numpy.random as npr

matplotlib.use('TkAgg')


parser = argparse.ArgumentParser(
    description="Run simulation of congestion under queue")
parser.add_argument(
    '--input', default=sys.stdin, type=argparse.FileType('r'),
    help="File to read JSON client measurements from")
args = parser.parse_args()

data = json.load(args.input)

params = data['SIM_PARAMS']


for k in data['CLIENT_DATA'][0].keys():
    if k == 'time':
        continue

    plt.figure()

    for i, client in enumerate(data['CLIENT_DATA']):
        xs = sorted(client[k])
        ys = np.arange(len(xs))/len(xs)

        plt.plot(xs, ys, label=f"Client {i}")

    if k in {'rtt', 'mrtt'}:
        plt.plot((params['BASE_RTT'], params['BASE_RTT']), (0, 1),
                 'k--', label='Base RTT')
    elif k in {'pacingRate', 'mu', 'ssthresh', 'integ'}:
        plt.plot((params['MU'], params['MU']), (0, 1),
                 'k--', label='mu')
        plt.plot((params['MU']/params['NUM_CLIENTS'], params['MU']/params['NUM_CLIENTS']), (0, 1),
                 'k:', label='mu/N')

    plt.xlabel(f"x ({k})")
    plt.ylabel("P(X < x)")
    plt.grid()
    plt.legend()

    #plt.savefig(f"figures/{k}.png")
plt.show()
