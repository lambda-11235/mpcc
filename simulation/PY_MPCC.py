
import math
import numpy as np
import numpy.random as npr

from CC import *


def wma(avg, x):
    return (9*avg + x)/10

def clamp(x, minimum, maximum):
    if x < minimum:
        return minimum
    elif x > maximum:
        return maximum
    else:
        return x


class PY_MPCC:
    def __init__(self, runInfo, bottleneckRate, targetRTT):
        self.bottleneckRate = bottleneckRate
        self.targetRTT = targetRTT

        self.minRate = runInfo.mss/runInfo.lastRTT
        self.minRTT = runInfo.lastRTT

        self.mrtt = runInfo.lastRTT
        self.devRTT = 0
        self.lastTime = runInfo.time

        self.rate = self.minRate
        #self.rate = npr.uniform(self.minRate, self.bottleneckRate/4)

        self.mu = self.minRate
        self.muDeliv = 0
        self.muTime = runInfo.time


    def pacingRate(self, runInfo):
        return self.rate

    def cwnd(self, runInfo):
        bdp = int(self.rate*self.targetRTT/runInfo.mss)
        return 1 + bdp


    def ack(self, runInfo):
        self.minRate = min(self.bottleneckRate/128, runInfo.mss/self.targetRTT)
        self.minRTT = min(self.minRTT, runInfo.lastRTT)

        rtt = runInfo.lastRTT
        if runInfo.inflight < 8:
            self.mrtt = rtt
        else:
            self.mrtt = wma(self.mrtt, rtt)

        self.devRTT = wma(self.devRTT, abs(rtt - self.mrtt))


        if runInfo.time > self.muTime + self.targetRTT:
            deliv = (runInfo.delivered - self.muDeliv)*runInfo.mss
            est = deliv/(runInfo.time - self.muTime)

            if self.mrtt > self.targetRTT:
                self.mu = est
            else:
                self.mu = max(self.mu, est)

            self.mu = clamp(self.mu, self.minRate, 2*self.bottleneckRate)

            self.muDeliv = runInfo.delivered
            self.muTime = runInfo.time


        self.lastTime = runInfo.time

        err = self.targetRTT - runInfo.lastRTT
        tau = max(4*self.targetRTT, runInfo.mss/self.mu)

        num = tau + err
        den = tau
        self.rate = (num*self.mu)/den #+ self.minRate
        self.rate = clamp(self.rate, self.minRate, 2*self.bottleneckRate)


    def loss(self, runInfo):
        pass


    def getDebugInfo(self):
        return {'mrtt': self.mrtt,
                'mu': self.mu}
