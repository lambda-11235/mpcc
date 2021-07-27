
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


class PID:
    def __init__(self, runInfo, bottleneckRate, targetRTT):
        self.bottleneckRate = bottleneckRate
        self.targetRTT = targetRTT

        self.minRate = min(self.bottleneckRate/128, runInfo.mss/self.targetRTT)
        self.minRTT = runInfo.lastRTT

        self.mrtt = runInfo.lastRTT
        self.devRTT = 0
        self.lastTime = runInfo.time
        self.lossCredit = 0

        self.integ = self.minRate
        self.rate = self.minRate
        self.ssthresh = self.bottleneckRate

        self.mu = self.minRate
        self.muDeliv = 0
        self.muTime = runInfo.time


    def pacingRate(self, runInfo):
        return self.rate

    def cwnd(self, runInfo):
        bdp = int(self.rate*self.targetRTT/runInfo.mss)
        return 1 + 2*bdp


    def ack(self, runInfo):
        self.minRate = min(self.bottleneckRate/128, runInfo.mss/self.targetRTT)
        self.minRTT = min(self.minRTT, runInfo.lastRTT)

        self.devRTT = wma(self.devRTT, abs(runInfo.lastRTT - self.mrtt))

        if runInfo.inflight < 8:
            self.mrtt = runInfo.lastRTT
        else:
            self.mrtt = wma(self.mrtt, runInfo.lastRTT)


        deliv = runInfo.delivered - self.muDeliv
        if runInfo.time > self.muTime + self.targetRTT and deliv > 0:
            est = deliv*runInfo.mss/(runInfo.time - self.muTime)

            if self.mrtt > self.targetRTT:
                self.mu = est
            else:
                self.mu = max(self.mu, est)

            self.mu = clamp(self.mu, self.minRate, 2*self.bottleneckRate)

            self.muDeliv = runInfo.delivered
            self.muTime = runInfo.time

        if self.mrtt > self.targetRTT:
            self.ssthresh = self.mu/2


        self.update(runInfo)


    def update(self, runInfo):
        err = self.targetRTT - runInfo.lastRTT
        err -= self.lossCredit

        tau = max(4*self.targetRTT, runInfo.mss/self.mu)

        kp = 2*self.mu/tau
        ki = self.mu/tau**2

        updatePeriod = 1.0e-2/max(1.0e-6, ki*abs(err))
        #print(f"updatePeriod = {updatePeriod} ~ {self.mrtt}")

        dt = runInfo.time - self.lastTime

        if dt > updatePeriod:
            self.lastTime = runInfo.time

            if self.rate < self.ssthresh:
                dIdt = self.rate/tau
            else:
                dIdt = ki*err
                #dIdt += self.minRate*self.targetRTT/tau**2

            self.integ += dIdt*dt
            self.rate = kp*err + self.integ

            self.lossCredit -= self.lossCredit*dt/tau

        self.integ = clamp(self.integ, self.minRate, 2*self.bottleneckRate)
        self.rate = clamp(self.rate, self.minRate, 2*self.bottleneckRate)


    def loss(self, runInfo):
        self.ssthresh = min(self.ssthresh, self.mu/2)

        self.lossCredit = self.targetRTT
        self.update(runInfo)


    def getDebugInfo(self):
        return {'mrtt': self.mrtt,
                'mu': self.mu,
                'integ': self.integ,
                'ssthresh': self.ssthresh,
                'lossCredit': self.lossCredit}
