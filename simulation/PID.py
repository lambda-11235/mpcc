
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


class PID:
    def __init__(self, runInfo, bottleneckRate, targetRTT):
        self.bottleneckRate = bottleneckRate
        self.targetRTT = targetRTT

        self.minRate = runInfo.mss/runInfo.lastRTT
        self.minRTT = runInfo.lastRTT

        self.mrtt = runInfo.lastRTT
        self.devRTT = 0
        self.lastTime = runInfo.time

        self.integ = self.minRate
        self.rate = self.minRate

        self.mu = self.bottleneckRate
        self.muACKed = 0
        self.muTime = runInfo.time


    def pacingRate(self, runInfo):
        return self.rate

    def cwnd(self, runInfo):
        return 2*self.rate*self.mrtt/runInfo.mss


    def ack(self, runInfo):
        self.minRate = runInfo.mss/self.targetRTT
        self.minRTT = min(self.minRTT, runInfo.lastRTT)

        if runInfo.inflight < 8:
            self.mrtt = runInfo.lastRTT
        else:
            self.mrtt = wma(self.mrtt, runInfo.lastRTT)

        self.devRTT = wma(self.devRTT, abs(runInfo.lastRTT - self.mrtt))


        self.muACKed += 1
        if runInfo.time > self.muTime + self.targetRTT:
            est = self.muACKed*runInfo.mss/(runInfo.time - self.muTime)

            if self.mrtt > self.targetRTT:
                self.mu = est
            else:
                self.mu = max(self.mu, est)

            self.mu = clamp(self.mu, self.minRate, 2*self.bottleneckRate)

            self.muACKed = 0
            self.muTime = runInfo.time


        err = self.targetRTT - self.mrtt
        tau = 4*self.targetRTT

        if self.mrtt < self.targetRTT - 8*self.devRTT:
            upper = self.targetRTT - runInfo.inflight*runInfo.mss/self.mu
            err = max(err, upper)


        kp = 2*self.mu/tau
        ki = self.mu/tau**2

        dt = runInfo.time - self.lastTime
        self.lastTime = runInfo.time

        self.integ += ki*err*dt
        self.integ += 0.1*self.minRate*dt/tau

        self.rate = kp*err + self.integ

        self.integ = clamp(self.integ, self.minRate, 2*self.bottleneckRate)
        self.rate = clamp(self.rate, self.minRate, 2*self.bottleneckRate)


    def loss(self, runInfo):
        self.startup = False
        self.integ = self.mu/2
        self.rate = self.minRate


    def getDebugInfo(self):
        return {'mrtt': self.mrtt,
                'mu': self.mu,
                'integ': self.integ}
