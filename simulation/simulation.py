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

#matplotlib.use('TkAgg')


# First  define some global variables
class G:
    NUM_CLIENTS = 4#0

    CLIENT_MARK = False
    SERVER_MARK = False

    ALPHA = 0.9

    MSS = 1500
    MU = 10*MSS

    BASE_RTT = 5.0#e-2
    TARGET_RTT = BASE_RTT + NUM_CLIENTS*MSS/MU
    #TARGET_RTT = BASE_RTT + MSS/MU
    #TARGET_RTT = 1.1*BASE_RTT

    MAX_SEQ = int(1000*MU*TARGET_RTT/MSS)

    #MIN_RTO = 0
    MIN_RTO = 2*TARGET_RTT + 4*NUM_CLIENTS*MSS/MU

    NUM_SEND = 1000
    MAX_PACKETS = max(MU*TARGET_RTT/MSS, 2*NUM_CLIENTS)

    SIM_TIME = 1000*NUM_SEND*MSS/MU
    START_TIME_OFFSETS = 0#SIM_TIME/(2*NUM_CLIENTS)

    def makeCC():
        runInfo = RuntimeInfo(0, G.BASE_RTT, 0, 0, G.MSS)
        bdp = G.MU*G.TARGET_RTT/G.MSS

        #return MPCC(runInfo, G.MU, G.TARGET_RTT)
        #return PY_MPCC(runInfo, G.MU, G.TARGET_RTT)
        #return CPID(runInfo, G.MU, G.TARGET_RTT)
        return PID(runInfo, G.MU, G.TARGET_RTT)
        #return AIMD(runInfo, G.MU, G.TARGET_RTT)
        #return ExactCC(1.1*G.MU/G.NUM_CLIENTS, 1e6*bdp)


class Statistics(object):
    def __init__(self):
        self.recs = {'time': [], 'delivered': [], 'losses': [],
                     'rtt': [], 'pacingRate': [], 'cwnd': []}

    def update(self, time, delivered, losses, rtt, pacingRate, cwnd, debugInfo):
        self.recs['time'].append(time)
        self.recs['delivered'].append(delivered)
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
    def __init__(self, sendTime, client, seq):
        self.sendTime = sendTime
        self.client = client
        self.seq = seq


class Server(object):
    def __init__(self, env, done):
        self.env = env
        self.queue = []
        self.action = env.process(self.run())

        self.done = done
        self.activeClients = G.NUM_CLIENTS
        self.totalDelivered = 0

    def run(self):
        # Generate packets at rate lambda and store in queue
        while self.activeClients > 0:
            p1 = 100*self.totalDelivered/(G.NUM_CLIENTS*G.NUM_SEND)
            p2 = 100*self.env.now/G.SIM_TIME
            print(f"{max(p1, p2):.2f}%", end='\r')

            if G.SERVER_MARK:
                t = npr.exponential(G.MSS/G.MU)
            else:
                t = G.MSS/G.MU

            yield self.env.timeout(t)

            if len(self.queue) > 0:
                p = self.queue.pop(0)
                p.client.ack(p)

            if env.now > G.SIM_TIME:
                self.done.succeed()

        self.done.succeed()

    def send(self, packet):
        yield self.env.timeout(G.BASE_RTT)

        if len(self.queue) < G.MAX_PACKETS:
            self.queue.append(packet)


class Client(object):
    def __init__(self, env, stats, server):
        self.env = env
        self.stats = stats
        self.server = server
        self.action = env.process(self.run())


        self.nextSeq = 0
        ## Number of acknowledgements for a sequence
        self.seqAcked = np.zeros(G.MAX_SEQ, dtype=int)
        ## Queue of sequence number for packets being sent
        self.queue = []

        self.devRTT = G.BASE_RTT
        self.mrtt = G.BASE_RTT

        self.delivered = 0
        self.losses = 0
        self.lastRTT = 0
        self.inflight = 0
        self.cc = G.makeCC()


    def run(self):
        # Generate packets at rate lambda and store in queue
        while self.delivered < G.NUM_SEND:
            runInfo = RuntimeInfo(self.env.now, self.lastRTT,
                                  self.delivered, self.inflight,
                                  G.MSS)

            if G.CLIENT_MARK:
                t = npr.exponential(G.MSS/self.cc.pacingRate(runInfo))
            else:
                t = G.MSS/self.cc.pacingRate(runInfo)

            yield self.env.timeout(t)

            if self.inflight < self.cc.cwnd(runInfo):
                if len(self.queue) == 0:
                    self.newPacket()

                seq = self.queue.pop(0)
                packet = Packet(self.env.now, self, seq)
                self.env.process(self.server.send(packet))

        self.server.activeClients -= 1


    def ack(self, packet):
        if self.seqAcked[packet.seq] == 0:
            self.inflight -= 1
            self.delivered += 1
            self.server.totalDelivered += 1

        self.lastRTT = self.env.now - packet.sendTime
        self.seqAcked[packet.seq] += 1

        self.devRTT = G.ALPHA*self.devRTT + (1 - G.ALPHA)*abs(self.lastRTT - self.mrtt)
        self.mrtt = G.ALPHA*self.mrtt + (1 - G.ALPHA)*self.lastRTT

        runInfo = RuntimeInfo(self.env.now, self.lastRTT,
                              self.delivered, self.inflight,
                              G.MSS)
        self.cc.ack(runInfo)

        self.stats.update(self.env.now, self.delivered,
                          self.losses, self.lastRTT,
                          self.cc.pacingRate(runInfo),
                          self.cc.cwnd(runInfo),
                          self.cc.getDebugInfo())


    def loss(self):
        self.losses += 1

        runInfo = RuntimeInfo(self.env.now, self.lastRTT,
                              self.delivered, self.inflight,
                              G.MSS)
        self.cc.loss(runInfo)

        self.stats.update(self.env.now, self.delivered,
                          self.losses, self.lastRTT,
                          self.cc.pacingRate(runInfo),
                          self.cc.cwnd(runInfo),
                          self.cc.getDebugInfo())


    def newPacket(self):
        seq = self.nextSeq
        self.nextSeq = (seq + 1)%G.MAX_SEQ
        self.seqAcked[seq] = 0

        self.inflight += 1

        self.queue.append(seq)
        self.env.process(self.watch(seq))

    def watch(self, seq):
        """
        Watch a packet for timeouts, and retransmit when necessary.
        """
        acked = False

        while not acked:
            rto = max(G.MIN_RTO, self.mrtt + 4*self.devRTT)
            yield self.env.timeout(rto)

            if self.seqAcked[seq] > 0:
                acked = True
            else:
                self.loss()
                self.queue.append(seq)


env = simpy.Environment()
done = env.event()
server = Server(env, done)

stats = [Statistics() for _ in range(G.NUM_CLIENTS)]

def startup(env):
    for i in range(G.NUM_CLIENTS):
        clients = Client(env, stats[i], server)
        yield env.timeout(G.START_TIME_OFFSETS)

env.process(startup(env))
env.run(until=done)#until=G.SIM_TIME)
print()


print(f"Base RTT: {G.BASE_RTT}")
print(f"Target RTT: {G.TARGET_RTT}")
print(f"MU: {G.MU}")

print("Mean Throughput")
delivs = []

for i in range(G.NUM_CLIENTS):
    if len(stats[i].recs['delivered']) > 0:
        delivs.append(stats[i].recs['delivered'][-1])
    else:
        delivs.append(0)

    throughput = delivs[-1]*G.MSS/env.now

    if False:
        print(f"\tClient {i}:\t{throughput:.3e}")

delivs = np.array(delivs)
total = sum(delivs)*G.MSS/env.now
fairness = sum(delivs)**2/(len(delivs)*sum(delivs**2))
print(f"\tTotal: {total} = {100*total/G.MU:.2f}% MU")
print(f"\tJain Fairness: {fairness}")

print()

losses = 0
for i in range(G.NUM_CLIENTS):
    if len(stats[i].recs['losses']) > 0:
        losses += stats[i].recs['losses'][-1]
lossRate = np.sum(losses)*G.MSS/env.now
print(f"Total Losses: {losses:.3e}")
print(f"Total Loss Rate: {lossRate:.3e} = {100*lossRate/G.MU:.2f}% MU")

print()

mrtts = []
IQRs = []
for i in range(G.NUM_CLIENTS):
    if len(stats[i].recs['rtt']) > 0:
        q1, q2, q3 = np.quantile(stats[i].recs['rtt'], [1/4, 1/2, 3/4])
        mrtts.append(q2)
        IQRs.append(q3 - q1)
print(f"Median of Client Median RTT: {np.median(mrtts)}")
print(f"Max of Client Median RTT: {np.max(mrtts)}")
print(f"Median of Client RTT IQRs: {np.median(IQRs)}")
print(f"Max of Client RTT IQRs: {np.max(IQRs)}")


if False:
    for k in stats[0].recs.keys():
        if k == 'time':
            continue

        print(f"{k}")

        for i in range(G.NUM_CLIENTS):
            v = stats[i].recs[k]
            q1, q2, q3 = np.quantile(v, [1/4, 1/2, 3/4])
            print(f"\tClient {i}:\tmean = {np.mean(v):.3e},\tstd = {np.std(v):.3e}")
            print(f"\t\tmedian = {q2:.3e},\tIQR = {(q3 - q1):.3e}")


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
        plt.plot((0, env.now/G.TARGET_RTT), (G.TARGET_RTT, G.TARGET_RTT),
                 'k--', label='Target RTT')
    elif k in {'pacingRate', 'mu', 'ssthresh', 'integ'}:
        plt.plot((0, env.now/G.TARGET_RTT), (G.MU, G.MU),
                 'k--', label='mu')
        plt.plot((0, env.now/G.TARGET_RTT), (G.MU/G.NUM_CLIENTS, G.MU/G.NUM_CLIENTS),
                 'k:', label='mu/N')
    elif k in {'delivered', 'losses'}:
        plt.plot((0, env.now/G.TARGET_RTT), (0, G.MU*env.now/G.MSS),
                 'k--', label='mu')
        plt.plot((0, env.now/G.TARGET_RTT), (0, G.MU*env.now/G.MSS/G.NUM_CLIENTS),
                 'k:', label='mu/N')

    plt.xlabel("Time (Target RTTs)")
    plt.ylabel(k)
    plt.grid()
    plt.legend()

    plt.savefig(f"figures/{k}.png")
