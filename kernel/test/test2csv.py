#!/usr/bin/python

import argparse
import json
import numpy as np
import pandas as pd

from data import Data

parser = argparse.ArgumentParser(description="Converts test results to a single CSV.")
parser.add_argument('test', type=str,
        help="The name of the test to analyze.")
parser.add_argument('csv_file', type=str,
        help="The CSV to output.")
parser.add_argument('stream', type=int, default=0,
        help="The stream to report.")
args = parser.parse_args()


data = Data(args.test)
s = data.streams[args.stream]

data = [s['start'], s['bits_per_second'], s['rtt'], s['retransmits']]
data = pd.concat(data, axis=1)

data.to_csv(args.csv_file, index=False)
