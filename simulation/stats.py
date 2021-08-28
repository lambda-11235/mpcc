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


print(f"Base RTT: {params['BASE_RTT']}")
#print(f"Target RTT: {params['TARGET_RTT']}")
print(f"MU: {params['MU']}")

print()


delivered = []
losses = 0
mrtts = []
IQRs = []
rtt99 = []
avgTargets = []

for client in data['CLIENT_DATA']:
    if len(client['delivered']) > 0:
        delivered.append(client['delivered'][-1])
    else:
        delivered.append(0)

    if len(client['losses']) > 0:
        losses += client['losses'][-1]

    if len(client['rtt']) > 0:
        q1, q2, q3, q4 = np.quantile(client['rtt'], [1/4, 1/2, 3/4, 0.99])
        mrtts.append(q2)
        IQRs.append(q3 - q1)
        rtt99.append(q4)

    if len(client['targetRTT']) > 0:
        avgTargets.append(np.mean(client['targetRTT']))


delivered = np.array(delivered)
total = sum(delivered)*params['MSS']/data['RUNTIME']
fairness = sum(delivered)**2/(len(delivered)*sum(delivered**2))
print(f"Goodput: {total} = {100*total/params['MU']:.2f}% MU")
print(f"Jain Fairness: {fairness}")

print()

lossRate = np.sum(losses)*params['MSS']/data['RUNTIME']
print(f"Total Losses: {losses:.3e}")
print(f"Total Loss Rate: {lossRate:.3e} = {100*lossRate/params['MU']:.2f}% MU")

print()

print(f"Median of Client Median RTT: {np.median(mrtts)}")
print(f"Max of Client Median RTT: {np.max(mrtts)}")
print(f"Median of Client RTT IQRs: {np.median(IQRs)}")
print(f"Max of Client RTT IQRs: {np.max(IQRs)}")
print(f"Median of Client RTT 99th: {np.median(rtt99)}")
print(f"Max of Client RTT 99th: {np.max(rtt99)}")

print()

print(f"Median of Client Average Target RTT: {np.median(avgTargets)}")
