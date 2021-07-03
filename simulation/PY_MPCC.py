
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

        self.mrtt = runInfo.lastRTT
        self.devRTT = 0
        self.lastTime = runInfo.time

        self.ref = self.targetRTT
        self.predRTT = self.mrtt
        self.err = 0
        self.rate = self.minRate
        #self.rate = npr.uniform(self.minRate, self.bottleneckRate/4)

        self.ssthresh = self.bottleneckRate
        self.recovery = False

        self.mu = self.rate
        self.muInteg = 0
        self.muRTT = self.mrtt
        self.muTime = 0
        self.muLastTime = 0


    def pacingRate(self, runInfo):
        return self.rate

    def cwnd(self, runInfo):
        return 2*self.rate*self.mrtt/runInfo.mss


    def ack(self, runInfo):
        self.minRate = wma(self.minRate, runInfo.mss/runInfo.lastRTT)

        rtt = runInfo.lastRTT
        if runInfo.inflight < 8:
            self.mrtt = rtt
        else:
            self.mrtt = wma(self.mrtt, rtt)

        self.devRTT = wma(self.devRTT, abs(rtt - self.mrtt))


        if self.mrtt > 2*self.targetRTT:
            self.loss(runInfo)
        elif self.mrtt > self.targetRTT:
            self.ssthresh = min(self.ssthresh, self.mu/4)

        self.updateMU(runInfo)

        if runInfo.time > self.lastTime + self.targetRTT:
            self.lastTime = runInfo.time
            self.ssthresh += self.minRate

            if self.mu < self.ssthresh and not self.recovery:
                self.ref = 2*self.targetRTT
                self.err = 0
            else:
                self.err = wma(self.err, self.mrtt - self.predRTT)
                self.ref = wma(self.mrtt, self.targetRTT)

            num = self.targetRTT - self.err + self.ref - self.mrtt
            den = self.targetRTT
            self.rate = (num*self.mu)/den

            self.predRTT = self.mrtt + self.targetRTT*(self.rate - self.mu)/self.mu


        self.rate = clamp(self.rate, self.minRate, 2*self.bottleneckRate)


    def loss(self, runInfo):
        self.rate = self.mu/2
        self.ssthresh = min(self.ssthresh, self.mu/4)
        self.recovery = True


    def updateMU(self, runInfo):
        cond1 = self.muTime > 4*(self.targetRTT + self.devRTT)
        cond2 = self.muTime > self.targetRTT and self.mrtt > 2*self.targetRTT

        if cond1 or cond2:
            est = self.muInteg/(self.muTime + self.mrtt - self.muRTT)
            #est = runInfo.inflight*runInfo.mss/runInfo.lastRTT

            if est > self.mu:
                est += self.minRate

            self.mu = est

            self.resetMUEst(runInfo)
            self.mu = clamp(self.mu, runInfo.mss/runInfo.lastRTT,
                            2*self.bottleneckRate)
        else:
            dt = runInfo.time - self.muLastTime
            self.muLastTime = runInfo.time

            self.muInteg += self.rate*dt
            self.muTime += dt


    def resetMUEst(self, runInfo):
        self.muInteg = 0
        self.muRTT = self.mrtt
        self.muTime = 0
        self.muLastTime = runInfo.time


    def getDebugInfo(self):
        return {'mrtt': self.mrtt,
                'mu': self.mu,
                'err': self.err,
                'rtt_ref': self.ref,
                'ssthresh': self.ssthresh}
