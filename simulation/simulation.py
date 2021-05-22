
import matplotlib
import matplotlib.pyplot as plt

import numpy as np
import numpy.random as npr

import simpy

from CC import RuntimeInfo, ExactCC, PY_MPCC

matplotlib.use('TkAgg')


# First  define some global variables
class G:
    NUM_CLIENTS = 4

    MM1 = True

    MU = 10.0
    MSS = 1

    BASE_RTT = 50.0
    TARGET_RTT = BASE_RTT + 1/MU + 10.0

    SIM_TIME = 100*TARGET_RTT

    def makeCC():
        #rate = (G.MU - 1/(G.TARGET_RTT - G.BASE_RTT))/G.NUM_CLIENTS
        #return ExactCC(rate, 2*rate*G.TARGET_RTT)

        runInfo = RuntimeInfo(0, G.BASE_RTT, 0, G.MSS)
        return PY_MPCC(runInfo, G.MU, G.TARGET_RTT, 1.0)


class Statistics(object):
    def __init__(self):
        self.recs = {'time': [], 'rtt': [], 'pacingRate': [], 'cwnd': []}

    def update(self, time, rtt, pacingRate, cwnd, debugInfo):
        self.recs['time'].append(time)
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
            
            if G.MM1:
                t = npr.exponential(1/G.MU)
            else:
                t = 1/G.MU

            yield self.env.timeout(t)

            if len(self.queue) > 0:
                p = self.queue.pop(0)
                p.client.ack(p)

    def send(self, packet):
        self.queue.append(packet)


class Client(object):
    def __init__(self, env, stats, server):
        self.env = env
        self.stats = stats
        self.server = server
        self.action = env.process(self.run())
        
        self.lastRTT = 0
        self.inflight = 0
        self.cc = G.makeCC()

        
    def run(self):
        # Generate packets at rate lambda and store in queue
        while True:
            runInfo = RuntimeInfo(self.env.now, self.lastRTT, self.inflight, G.MSS)

            if G.MM1:
                t = npr.exponential(1/self.cc.pacingRate(runInfo))
            else:
                t = 1/self.cc.pacingRate(runInfo)
            
            yield self.env.timeout(t)

            if self.inflight < self.cc.cwnd(runInfo):
                self.env.process(self.send(Packet(self.env.now, self)))
                self.inflight += 1


    def ack(self, packet):
        self.inflight -= 1

        self.lastRTT = self.env.now - packet.sendTime

        runInfo = RuntimeInfo(self.env.now, self.lastRTT, self.inflight, G.MSS)
        self.cc.ack(runInfo)

        self.stats.update(self.env.now, self.lastRTT,
                          self.cc.pacingRate(runInfo),
                          self.cc.cwnd(runInfo),
                          self.cc.getDebugInfo())


    def send(self, packet):
        yield self.env.timeout(G.BASE_RTT)
        self.server.send(packet)


env = simpy.Environment()
stats = [Statistics() for _ in range(G.NUM_CLIENTS)]

server = Server(env)
clients = [Client(env, stats[i], server) for i in range(G.NUM_CLIENTS)]

env.run(until=G.SIM_TIME)
print()


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

    if k == 'rtt':
        plt.plot((0, G.SIM_TIME/G.TARGET_RTT), (G.TARGET_RTT, G.TARGET_RTT),
                 'k--', label='Target RTT')
    elif k in {'pacingRate', 'rb'}:
        plt.plot((0, G.SIM_TIME/G.TARGET_RTT), (G.MU, G.MU),
                 'k--', label='mu')
        plt.plot((0, G.SIM_TIME/G.TARGET_RTT), (G.MU/G.NUM_CLIENTS, G.MU/G.NUM_CLIENTS),
                 'k:', label='mu/N')

    plt.xlabel("Time (Target RTTs)")
    plt.ylabel(k)
    plt.legend()

    plt.savefig(f"figures/{k}.png")
