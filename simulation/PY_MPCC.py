
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
        self.ssthresh = 0#2*self.maxRate*runInfo.lastRTT/runInfo.mss

        self.mrtt = runInfo.lastRTT
        self.devRTT = 0
        self.lastTime = runInfo.time

        self.ref = self.target_rtt
        self.predRTT = self.mrtt
        self.err = 0
        #self.rate = 2*self.maxRate
        self.rate = npr.uniform(self.minRate, self.maxRate/4)

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

        self.updateMU(runInfo)

        if self.inSlowStart():
            if self.mrtt > self.target_rtt:
                self.loss(runInfo)
            elif runInfo.time > self.lastTime + self.target_rtt:
                self.lastTime = runInfo.time

                self.bdp = self._cwnd
                self._cwnd *= 2
                self.rate = 2*self._cwnd*runInfo.mss/self.target_rtt
        elif runInfo.time > self.lastTime + self.target_rtt:
            self.lastTime = runInfo.time

            a = 0.9
            self.err = a*self.err + (1 - a)*(self.mrtt - self.predRTT)
            ref = a*self.mrtt + (1 - a)*self.target_rtt

            num = self.target_rtt - self.err + ref - self.mrtt
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
        self._cwnd = 0.9*self.bdp
        self.ssthresh = self._cwnd/2

        self.lastTime = runInfo.time
        self.rate = self._cwnd*runInfo.mss/self.target_rtt

        self._cwnd = max(1, self._cwnd)
        self.rate = min(max(self.rate, self.minRate), 2*self.maxRate)

        self.mu = self.rate
        self.resetMUEst(runInfo)


    def updateMU(self, runInfo):
        if self.muTime > 4*(self.target_rtt + self.devRTT) or self.mrtt > 2*self.target_rtt:
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


    def inSlowStart(self):
        return self._cwnd < self.ssthresh


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
