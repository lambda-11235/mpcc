#!/usr/bin/env python

import argparse
import json
import sys

import matplotlib
import matplotlib.pyplot as plt

import numpy as np
import numpy.random as npr

#matplotlib.use('TkAgg')


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
        ts = client['time']
        ts = np.array(ts)/params['TARGET_RTT']

        vs = client[k]

        plt.plot(ts, vs, label=f"Client {i}")

    if k in {'rtt', 'mrtt'}:
        plt.plot((0, data['RUNTIME']/params['TARGET_RTT']), (params['TARGET_RTT'], params['TARGET_RTT']),
                 'k--', label='Target RTT')
    elif k in {'pacingRate', 'mu', 'ssthresh', 'integ'}:
        plt.plot((0, data['RUNTIME']/params['TARGET_RTT']), (params['MU'], params['MU']),
                 'k--', label='mu')
        plt.plot((0, data['RUNTIME']/params['TARGET_RTT']), (params['MU']/params['NUM_CLIENTS'], params['MU']/params['NUM_CLIENTS']),
                 'k:', label='mu/N')
    elif k in {'delivered', 'losses'}:
        plt.plot((0, data['RUNTIME']/params['TARGET_RTT']), (0, params['MU']*data['RUNTIME']/params['MSS']),
                 'k--', label='mu')
        plt.plot((0, data['RUNTIME']/params['TARGET_RTT']), (0, params['MU']*data['RUNTIME']/params['MSS']/params['NUM_CLIENTS']),
                 'k:', label='mu/N')

    plt.xlabel("Time (Target RTTs)")
    plt.ylabel(k)
    plt.grid()
    plt.legend()

    #plt.savefig(f"figures/{k}.png")
plt.show()
