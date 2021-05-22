#!/usr/bin/python3

import threading
import time
import os

mpcccSysfs = '/sys/kernel/mpccc'

class RateSysfs:
    """
    Sets the minimum and maximum pacing rate for a process. It does this
    continually in a separate thread, so that when the process opens a port it
    gets set.
    """
    def __init__(self, rates, dest, ports, allPorts=False, delay=0.25):
        """
        `rates` are pairs of rates to be cycled through for each stream.
        `dest` is the destination address to set for.
        `ports` are the affected outgoing ports.
        `allPorts` triggers to set all outgoing connections.
        """
        self.rates = rates
        self.allPorts = allPorts
        self.delay = delay
        self.dest = dest
        self.ports = ports

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

        if self.rates is not None:
            while running:
                self.setMinMaxRate()
                time.sleep(self.delay)

                with self.lock:
                    running = self.running

    def setMinMaxRate(self):
        try:
            subdirs = os.listdir(mpcccSysfs)
            rateIdx = 0

            for mpcid in subdirs:
                filename = mpcccSysfs + '/' + mpcid
                mpcDest = 0
                mpcPort = 0

                with open(filename + '/daddr') as f:
                    mpcDest = int(f.read())

                with open(filename + '/dport') as f:
                    mpcPort = int(f.read())

                if self.allPorts or (mpcDest == self.dest and mpcPort in self.ports):
                    with open(filename + '/min_rate', 'w') as f:
                        f.write(str(self.rates[rateIdx][0]))

                    with open(filename + '/max_rate', 'w') as f:
                        f.write(str(self.rates[rateIdx][1]))

                    rateIdx = (rateIdx + 1)%len(self.rates)
        except Exception as e:
            print("Could not set min/max rate: {}.".format(e))

            with self.lock:
                self.running = False
