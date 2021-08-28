
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
    def __init__(self, runInfo, bottleneckRate, baseRTT, coalesce):
        self.bottleneckRate = bottleneckRate
        self.baseRTT = baseRTT
        self.coalesce = coalesce

        self.minRate = min(self.bottleneckRate/128, runInfo.mss/self.baseRTT)

        self.srtt = runInfo.lastRTT
        self.srttLastTime = runInfo.time

        self.tau = max(4*baseRTT, runInfo.mss/self.bottleneckRate)
        self.targetRTT = baseRTT

        self.rateLastTime = runInfo.time
        self.rttLastTime = runInfo.time

        self.integ = self.minRate
        self.rate = self.minRate
        self.slowStart = True

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
        self.tau = max(4*self.baseRTT, runInfo.mss/self.bottleneckRate)

        self.updateSRTT(runInfo)

        deliv = runInfo.delivered - self.muDeliv
        if runInfo.time > self.muTime + self.targetRTT and deliv > 0:
            est = deliv*runInfo.mss/(runInfo.time - self.muTime)

            if self.srtt > self.targetRTT:
                self.mu = est
            else:
                self.mu = max(self.mu, est)

            self.mu = clamp(self.mu, self.minRate, 2*self.bottleneckRate)

            self.muDeliv = runInfo.delivered
            self.muTime = runInfo.time

        self.update(runInfo)


    def loss(self, runInfo):
        self.slowStart = False
        self.update(runInfo)


    def update(self, runInfo):
        self.updateTargetRTT(runInfo)
        self.updateRate(runInfo)


    def updateSRTT(self, runInfo):
        dt = runInfo.time - self.srttLastTime

        diffSRTT = runInfo.lastRTT - self.srtt
        diffSRTT *= min(1, dt/self.baseRTT)

        if diffSRTT != 0:
            self.srttLastTime = runInfo.time

            self.srtt += diffSRTT


    def updateTargetRTT(self, runInfo):
        dt = runInfo.time - self.rttLastTime

        nt = self.baseRTT
        nt += (self.coalesce + runInfo.hops)*runInfo.mss/self.bottleneckRate
        nt += runInfo.mss/self.mu

        diffTargetRTT = (nt - self.targetRTT)
        diffTargetRTT *= min(1, dt/self.tau)

        if diffTargetRTT != 0:
            self.rttLastTime = runInfo.time

            self.targetRTT += diffTargetRTT
            self.targetRTT = max(self.baseRTT, self.targetRTT)
        

    def updateRate(self, runInfo):
        dt = runInfo.time - self.rateLastTime

        err = self.targetRTT - runInfo.lastRTT

        kp = 2*self.mu/self.tau
        ki = self.mu/self.tau**2

        if self.slowStart:
            diffInteg = self.rate
            diffInteg *= min(1, dt/self.tau)
        else:
            diffInteg = ki*err
            diffInteg *= min(self.tau, dt)

        if diffInteg != 0:
            self.rateLastTime = runInfo.time

            self.integ += diffInteg
            self.rate = kp*err + self.integ

        self.integ = clamp(self.integ, self.minRate, 2*self.bottleneckRate)
        self.rate = clamp(self.rate, self.minRate, 2*self.bottleneckRate)


    def getDebugInfo(self):
        return {'srtt': self.srtt,
                'tau': self.tau,
                'mu': self.mu,
                'integ': self.integ,
                'targetRTT': self.targetRTT,
                'slowStart': int(self.slowStart)}
