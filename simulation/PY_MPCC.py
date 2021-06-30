
import numpy as np
import numpy.random as npr

from CC import *


class PY_MPCC:
    def __init__(self, runInfo, mu, target_rtt, base_rtt):
        self.maxRate = mu
        self.target_rtt = target_rtt
        self.T = target_rtt

        self.alpha = 0.0

        self.minRate = runInfo.mss/runInfo.lastRTT

        self.bdp = 1
        self._cwnd = 1

        self.mrtt = runInfo.lastRTT
        self.devRTT = 0
        self.lastTime = runInfo.time

        self.ref = self.target_rtt
        self.predRTT = self.mrtt
        self.err = 0
        self.rate = self.minRate
        #self.rate = npr.uniform(self.minRate, self.maxRate/4)

        self.ssthresh = self.maxRate
        self.recovery = False

        self.mu = self.rate
        self.muInteg = 0
        self.muRTT = self.mrtt
        self.muTime = 0
        self.muLastTime = 0


    def pacingRate(self, runInfo):
        return self.rate

    def cwnd(self, runInfo):
        return self._cwnd


    def ack(self, runInfo):
        self.updateAlpha(runInfo)
        self.updateMinRate(runInfo)

        rtt = runInfo.lastRTT
        self.mrtt = self.wma(self.mrtt, rtt)
        self.devRTT = self.wma(self.devRTT, abs(rtt - self.mrtt))

        if self.mrtt > 2*self.target_rtt:
            self.loss(runInfo)
        elif self.mrtt > self.target_rtt:
            self.ssthresh = min(self.ssthresh, self.mu/4)

        self.updateMU(runInfo)

        if runInfo.time > self.lastTime + self.target_rtt:
            self.lastTime = runInfo.time
            self.ssthresh += self.minRate

            if self.mu < self.ssthresh and not self.recovery:
                self.ref = 2*self.target_rtt
                self.err = 0
            else:
                a = 0.9
                self.err = a*self.err + (1 - a)*(self.mrtt - self.predRTT)
                self.ref = a*self.mrtt + (1 - a)*self.target_rtt

            num = self.target_rtt - self.err + self.ref - self.mrtt
            den = self.target_rtt
            self.rate = num/den*self.mu

            self.predRTT = self.mrtt + self.target_rtt*(self.rate - self.mu)/self.mu

            self.bdp = self.rate*self.target_rtt/runInfo.mss
            self._cwnd = 2*self.bdp

            if self.mrtt > self.target_rtt:
                self.ssthresh = min(self.ssthresh, self.bdp)


        self._cwnd = max(1, self._cwnd)
        self.rate = min(max(self.rate, self.minRate), 2*self.maxRate)


    def loss(self, runInfo):
        self.rate = self.mu/2
        self.ssthresh = min(self.ssthresh, self.mu/4)
        self.recovery = True


    def updateMU(self, runInfo):
        cond1 = self.muTime > 4*(self.target_rtt + self.devRTT)
        cond2 = self.muTime > self.target_rtt and self.mrtt > 2*self.target_rtt

        if cond1 or cond2:
            est = self.muInteg/(self.muTime + self.mrtt - self.muRTT)
            #est = runInfo.inflight*runInfo.mss/runInfo.lastRTT

            if est > self.mu:
                est += self.minRate

            self.mu = est

            self.resetMUEst(runInfo)
            self.mu = min(max(runInfo.mss/runInfo.lastRTT, self.mu), 2*self.maxRate)
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


    def wma(self, avg, x):
        return self.alpha*avg + (1 - self.alpha)*x

    def updateAlpha(self, runInfo):
        self.alpha = 0.9*(1 - 1/max(1, runInfo.inflight))

    def updateMinRate(self, runInfo):
        self.minRate = runInfo.mss/self.mrtt
