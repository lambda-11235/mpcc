#!/usr/bin/env python

import matplotlib
import matplotlib.pyplot as plt

import numpy as np
import numpy.random as npr

import simpy

from CC import *
from MPCC import MPCC
from PY_MPCC import PY_MPCC
from CPID import CPID
from PID import PID

matplotlib.use('TkAgg')


# First  define some global variables
class G:
    NUM_CLIENTS = 4

    CLIENT_MARK = True
    SERVER_MARK = True

    MSS = 1500
    MU = 10*MSS

    BASE_RTT = 500.0
    SIGMA = 1
    TARGET_RTT = BASE_RTT + 2*MU*SIGMA**2/(np.sqrt(4*MU**2*SIGMA**2 + 1) - 1)
    #TARGET_RTT = BASE_RTT + 1/MU + 5

    MAX_PACKETS = MU*TARGET_RTT/MSS

    SIM_TIME = 1000*TARGET_RTT
    START_TIME_OFFSETS = 0#SIM_TIME/(2*NUM_CLIENTS)

    def makeCC():
        runInfo = RuntimeInfo(0, G.BASE_RTT, 0, G.MSS)
        rate = G.MU - 1/(G.TARGET_RTT - G.BASE_RTT)
        cwnd = rate*G.TARGET_RTT

        #return MPCC(runInfo, G.MU, G.TARGET_RTT)
        #return PY_MPCC(runInfo, G.MU, G.TARGET_RTT)
        return CPID(runInfo, G.MU, G.TARGET_RTT)
        #return PID(runInfo, G.MU, G.TARGET_RTT)
        #return AIMD(runInfo, G.MU, G.TARGET_RTT)
        #return ExactCC(rate, 1e6*cwnd)


class Statistics(object):
    def __init__(self):
        self.delivered = 0
        self.recs = {'time': [], 'losses': [], 'rtt': [], 'pacingRate': [], 'cwnd': []}

    def update(self, time, losses, rtt, pacingRate, cwnd, debugInfo):
        self.delivered += 1

        self.recs['time'].append(time)
        self.recs['losses'].append(losses)
        self.recs['rtt'].append(rtt)
        self.recs['pacingRate'].append(pacingRate)
        self.recs['cwnd'].append(cwnd)

        for k, v in debugInfo.items():
            if k in {'time', 'rtt', 'pacingRate', 'cwnd'}:
                continue

            if k not in self.recs.keys():
                self.recs[k] = []

            self.recs[k].append(v)


class Packet(object):
    def __init__(self, sendTime, client):
        self.sendTime = sendTime
        self.client = client


class Server(object):
    def __init__(self, env):
        self.env = env
        self.queue = []
        self.action = env.process(self.run())

    def run(self):
        # Generate packets at rate lambda and store in queue
        while True:
            print(f"{100*self.env.now/G.SIM_TIME:.2f}%", end='\r')

            if G.SERVER_MARK:
                t = npr.exponential(G.MSS/G.MU)
            else:
                t = G.MSS/G.MU

            yield self.env.timeout(t)

            if len(self.queue) > 0:
                p = self.queue.pop(0)
                p.client.ack(p)

    def send(self, packet):
        if len(self.queue) >= G.MAX_PACKETS:
            packet.client.loss()
        else:
            self.queue.append(packet)


class Client(object):
    def __init__(self, env, stats, server):
        self.env = env
        self.stats = stats
        self.server = server
        self.action = env.process(self.run())

        self.losses = 0
        self.lastRTT = 0
        self.inflight = 0
        self.cc = G.makeCC()


    def run(self):
        # Generate packets at rate lambda and store in queue
        while True:
            runInfo = RuntimeInfo(self.env.now, self.lastRTT, self.inflight, G.MSS)

            if G.CLIENT_MARK:
                t = npr.exponential(G.MSS/self.cc.pacingRate(runInfo))
            else:
                t = G.MSS/self.cc.pacingRate(runInfo)

            yield self.env.timeout(t)

            if self.inflight < self.cc.cwnd(runInfo):
                self.env.process(self.send(Packet(self.env.now, self)))
                self.inflight += 1


    def ack(self, packet):
        self.inflight -= 1

        self.lastRTT = self.env.now - packet.sendTime

        runInfo = RuntimeInfo(self.env.now, self.lastRTT, self.inflight, G.MSS)
        self.cc.ack(runInfo)

        self.stats.update(self.env.now, self.losses, self.lastRTT,
                          self.cc.pacingRate(runInfo),
                          self.cc.cwnd(runInfo),
                          self.cc.getDebugInfo())


    def loss(self):
        self.inflight -= 1
        self.losses += 1

        runInfo = RuntimeInfo(self.env.now, self.lastRTT, self.inflight, G.MSS)
        self.cc.loss(runInfo)

        self.stats.update(self.env.now, self.losses, self.lastRTT,
                          self.cc.pacingRate(runInfo),
                          self.cc.cwnd(runInfo),
                          self.cc.getDebugInfo())


    def send(self, packet):
        yield self.env.timeout(G.BASE_RTT)
        self.server.send(packet)

    def __init__(self, env, stats, server):
        self.env = env
        self.stats = stats
        self.server = server
        self.action = env.process(self.run())

        self.losses = 0
        self.lastRTT = 0
        self.inflight = 0
        self.cc = G.makeCC()


env = simpy.Environment()
stats = [Statistics() for _ in range(G.NUM_CLIENTS)]

def startup(env):
    server = Server(env)

    for i in range(G.NUM_CLIENTS):
        clients = Client(env, stats[i], server)
        yield env.timeout(G.START_TIME_OFFSETS)

    while True:
        yield env.timeout(G.SIM_TIME)

env.process(startup(env))
env.run(until=G.SIM_TIME)
print()


print(f"Base RTT: {G.BASE_RTT}")
print(f"Target RTT: {G.TARGET_RTT}")

print("Mean Throughput")
for i in range(G.NUM_CLIENTS):
    throughput = stats[i].delivered/G.SIM_TIME
    print(f"\tClient {i}:\t{throughput:.3e}")

for k in stats[0].recs.keys():
    if k == 'time':
        continue

    print(f"{k}")

    for i in range(G.NUM_CLIENTS):
        v = stats[i].recs[k]
        print(f"\tClient {i}:\tmean = {np.mean(v):.3e},\tstd = {np.std(v):.3e}")


for k in stats[0].recs.keys():
    if k == 'time':
        continue

    plt.figure()

    for i in range(G.NUM_CLIENTS):
        ts = stats[i].recs['time']
        ts = np.array(ts)/G.TARGET_RTT

        vs = stats[i].recs[k]

        plt.plot(ts, vs, label=f"Client {i}")

    if k in {'rtt', 'mrtt'}:
        plt.plot((0, G.SIM_TIME/G.TARGET_RTT), (G.TARGET_RTT, G.TARGET_RTT),
                 'k--', label='Target RTT')
    elif k in {'pacingRate', 'mu', 'ssthresh', 'integ'}:
        plt.plot((0, G.SIM_TIME/G.TARGET_RTT), (G.MU, G.MU),
                 'k--', label='mu')
        plt.plot((0, G.SIM_TIME/G.TARGET_RTT), (G.MU/G.NUM_CLIENTS, G.MU/G.NUM_CLIENTS),
                 'k:', label='mu/N')

    plt.xlabel("Time (Target RTTs)")
    plt.ylabel(k)
    plt.grid()
    plt.legend()

    plt.savefig(f"figures/{k}.png")
