
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


class PID_CWND:
    def __init__(self, runInfo, bottleneckRate, targetRTT):
        self.bottleneckRate = bottleneckRate
        self.targetRTT = targetRTT

        self.maxCWND = self.bottleneckRate*self.targetRTT/runInfo.mss
        self.minCWND = min(1, 1.0e-2*self.maxCWND)

        self.minRTT = runInfo.lastRTT

        self.mrtt = runInfo.lastRTT
        self.devRTT = 0
        self.lastTime = runInfo.time

        self.startup = True
        self.integ = 1
        self._cwnd = 1

        self.mu = 1.0e-3*self.bottleneckRate
        self.muACKed = 0
        self.muTime = runInfo.time


    def pacingRate(self, runInfo):
        rate = self._cwnd*runInfo.mss/self.targetRTT
        if self._cwnd < 1:
            return rate
        else:
            return self.bottleneckRate

    def cwnd(self, runInfo):
        if self._cwnd < 1:
            return 1
        else:
            return self._cwnd


    def ack(self, runInfo):
        self.maxCWND = self.bottleneckRate*self.targetRTT/runInfo.mss
        self.minCWND = min(1, 1.0e-2*self.maxCWND)

        self.minRTT = min(self.minRTT, runInfo.lastRTT)
        self.mrtt = wma(self.mrtt, runInfo.lastRTT)
        self.devRTT = wma(self.devRTT, abs(runInfo.lastRTT - self.mrtt))


        if self.mrtt > self.targetRTT:
            self.startup = False

        err = self.targetRTT - runInfo.lastRTT
        tau = 4*self.targetRTT
        
        if self.startup:
            err *= self.targetRTT/(self.targetRTT - self.minRTT)

        kp = 0#self.mu/runInfo.mss
        ki = self.mu/(runInfo.mss*tau)


        self.muACKed += 1
        if runInfo.time > self.muTime + tau:
            est = self.muACKed*runInfo.mss/(runInfo.time - self.muTime)

            if self.mrtt > self.targetRTT:
                self.mu = est
            else:
                self.mu = max(self.mu, est)

            self.mu = clamp(self.mu, 1.0e-3*self.bottleneckRate, 2*self.bottleneckRate)

            self.muACKed = 0
            self.muTime = runInfo.time


        dt = runInfo.time - self.lastTime

        self.lastTime = runInfo.time

        self.integ += ki*err*dt + self.minCWND/tau*dt
        self._cwnd = kp*err + self.integ

        self.integ = clamp(self.integ, self.minCWND, self.maxCWND)
        self._cwnd = clamp(self._cwnd, self.minCWND, self.maxCWND)


    def loss(self, runInfo):
        if self.startup:
            self.startup = False
            self.integ = self.mu*self.targetRTT/(2*runInfo.mss)
            self._cwnd = self.integ


    def getDebugInfo(self):
        return {'mrtt': self.mrtt,
                'mu': self.mu,
                'integ': self.integ}
