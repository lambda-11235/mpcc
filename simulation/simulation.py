#!/usr/bin/env python

import argparse
import json
import sys

import numpy as np
import numpy.random as npr

import simpy

from CC import *
from MPCC import MPCC
from PY_MPCC import PY_MPCC
from CPID import CPID
from PID import PID

#matplotlib.use('TkAgg')


parser = argparse.ArgumentParser(
    description="Run simulation of congestion under queue")
parser.add_argument(
    '--output', default=sys.stdout, type=argparse.FileType('w'),
    help="File to write JSON client measurements to.")
args = parser.parse_args()


# First  define some global variables
class G:
    NUM_CLIENTS = 40

    CLIENT_MARK = False
    SERVER_MARK = False

    ALPHA = 0.9

    MSS = 1500
    MU = 100*MSS

    BASE_RTT = 5.0e-2
    TARGET_RTT = BASE_RTT + NUM_CLIENTS*MSS/MU
    #TARGET_RTT = BASE_RTT + MSS/MU
    #TARGET_RTT = 1.1*BASE_RTT

    MAX_SEQ = int(1000*MU*TARGET_RTT/MSS)

    MIN_RTO = 0
    #MIN_RTO = 2*TARGET_RTT + 4*NUM_CLIENTS*MSS/MU

    NUM_SEND = 10000
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


clientData = []
for i in range(G.NUM_CLIENTS):
    clientData.append(stats[i].recs)

data = {'CLIENT_DATA': clientData,
        'RUNTIME': env.now,
        'SIM_PARAMS': {
            'NUM_CLIENTS': G.NUM_CLIENTS,
            'CLIENT_MARK': G.CLIENT_MARK,
            'SERVER_MARK': G.SERVER_MARK,
            'ALPHA': G.ALPHA,
            'MSS': G.MSS,
            'MU': G.MU,
            'BASE_RTT': G.BASE_RTT,
            'TARGET_RTT': G.TARGET_RTT,
            'MAX_SEQ': G.MAX_SEQ,
            'MIN_RTO': G.MIN_RTO,
            'NUM_SEND': G.NUM_SEND,
            'MAX_PACKETS': G.MAX_PACKETS,
            'SIM_TIME': G.SIM_TIME,
            'START_TIME_OFFSETS': G.START_TIME_OFFSETS
        }}

json.dump(data, args.output)
args.output.close()
