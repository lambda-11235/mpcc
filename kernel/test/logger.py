#!/usr/bin/python3

import argparse
import datetime
import glob
import json
import threading
import time
import os

def now():
    dt = datetime.datetime.now()
    return float("{}.{}".format(dt.strftime("%s"), dt.microsecond))

class Logger:
    def __init__(self, output, interval, verbose = False):
        self.output = output
        self.interval = interval
        self.verbose = verbose

        self.running = True
        self.lock = threading.Lock()
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target = self.run)
        self.thread.start()

    def stop(self):
        with self.lock:
            self.running = False

        self.thread.join()

    def run(self):
        running = True

        data = []
        outputF = open(self.output, mode = 'w')

        while running:
            t = now()

            for mpc in glob.glob("/sys/kernel/debug/mpcc/*"):
                try:
                    info = {'time': t, 'id': os.path.basename(mpc)}
                    for m in ['daddr', 'dport', 'lport',
                            "INT_BPS", "set_rate", "target_rtt",
                            "rb", "lp", "lb", "rtt_avg"]:
                        with open(mpc + "/" + m) as f:
                            info[m] = int(f.read())

                    data.append(info)

                    if self.verbose:
                        print("RTT (ms): {}, Set Rate (bytes/s): {}".format(
                            info['avg_rtt']/1000.0, info['set_rate']))

                except FileNotFoundError as err:
                    print(err)
                    pass

            s = self.interval - (now() - t)
            if s > 0:
                time.sleep(s)

            with self.lock:
                running = self.running

        json.dump(data, outputF, indent = 4)
