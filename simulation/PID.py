
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

        self.minRate = runInfo.mss/runInfo.lastRTT
        self.minRTT = runInfo.lastRTT

        self.mrtt = runInfo.lastRTT
        self.devRTT = 0
        self.lastTime = runInfo.time

        self.integ = self.minRate
        self.rate = self.minRate

        self.mu = self.bottleneckRate
        self.muDeliv = 0
        self.muTime = runInfo.time


    def pacingRate(self, runInfo):
        return self.rate

    def cwnd(self, runInfo):
        bdp = int(self.rate*self.targetRTT/runInfo.mss)
        return max(1, math.ceil(2*bdp))


    def ack(self, runInfo):
        self.minRate = min(self.bottleneckRate/128, runInfo.mss/self.targetRTT)
        self.minRTT = min(self.minRTT, runInfo.lastRTT)

        if runInfo.inflight < 8:
            self.mrtt = runInfo.lastRTT
        else:
            self.mrtt = wma(self.mrtt, runInfo.lastRTT)

        self.devRTT = wma(self.devRTT, abs(runInfo.lastRTT - self.mrtt))


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


        err = self.targetRTT - runInfo.lastRTT
        tau = max(4*self.targetRTT, runInfo.mss/self.mu)

        kp = 2*self.mu/tau
        ki = self.mu/tau**2

        updatePeriod = 1.0e-2/max(1.0e-6, ki*abs(err))
        #print(f"updatePeriod = {updatePeriod} ~ {self.mrtt}")

        dt = runInfo.time - self.lastTime

        if dt > updatePeriod:
            self.lastTime = runInfo.time

            dIdt = ki*err + 0.1*self.minRate*self.targetRTT/tau**2
            self.integ += dIdt*dt
            self.rate = kp*err + self.integ

        self.integ = clamp(self.integ, self.minRate, 2*self.bottleneckRate)
        self.rate = clamp(self.rate, self.minRate, 2*self.bottleneckRate)


    def loss(self, runInfo):
        self.integ = min(self.integ, self.mu - self.minRate)


    def getDebugInfo(self):
        return {'mrtt': self.mrtt,
                'mu': self.mu,
                'integ': self.integ}
