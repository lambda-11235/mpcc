#!/usr/bin/env python3

import argparse
import json
import numpy as np
import pandas as pd

from data import Data

parser = argparse.ArgumentParser(description="Statistically analyzes test results.")
parser.add_argument('test', type=str,
        help="The name of the test to analyze.")
args = parser.parse_args()


data = Data(args.test)

#print("For BWCtl")
#print(data.stream[['bits_per_second', 'rtt', 'rttvar', 'retransmits', 'snd_cwnd']].describe())

for stream in data.streams:
    print("Socket: {}".format(stream.socket[0]))
    print("Mean RTT: {}".format(stream.rtt.mean()))
    print("RTT Std: {}".format(stream.rtt.std()))
    print("Mean Rate: {:e} mbps".format(stream.bits_per_second.mean()/(1<<20)))
    print("Rate Std: {:e} mbps".format(stream.bits_per_second.std()/(1<<20)))
    print("Total Losses: {}".format(stream.retransmits.sum()))
    print("")

#print("\nFor Kernel Module")
#print(data.module[['rtt_meas_us', 'rate_set']].describe())
#
#idRTTMean = pd.DataFrame(columns=['id', 'mean_rtt_meas_us', 'rtt_std'])
#for x in data.module.groupby('id'):
#    idRTTMean = idRTTMean.append({'id': x[0],
#        'mean_rtt_meas_us': x[1].rtt_meas_us.mean(),
#        'rtt_std': x[1].rtt_meas_us.std()},
#        ignore_index = True)
#
#print(idRTTMean)
