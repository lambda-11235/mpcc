
import numpy as np
import numpy.random as npr

from CC import *


class MUEst:
    def __init__(self, runInfo, maxUnder, mu0):
        self.maxUnder = maxUnder
        self.underCnt = 0

        self.lastTime = runInfo.time
        self.mu = mu0
        #self.mu = npr.exponential(self.mu)

        self.reset(runInfo)

    def get(self):
        return self.mu

    def reset(self, runInfo):
        self.startRTT = runInfo.lastRTT
        self.integ = 0
        self.totalTime = 0

    def hardReset(self, runInfo, mu):
        self.mu = mu
        self.reset(runInfo)

    def update(self, runInfo, rate):
        dt = runInfo.time - self.lastTime
        self.lastTime = runInfo.time

        if self.totalTime > runInfo.lastRTT:
            est = self.integ/(self.totalTime + runInfo.lastRTT - self.startRTT)
            #est = runInfo.inflight*runInfo.mss/runInfo.lastRTT

            # Note that underCnt implementation is slightly
            # different than for PID.  This bacause we use mu to
            # directly compute the rate in MPCC, while for PID it
            # mostly accelerates convergence.
            if self.mu < est:
                self.underCnt += 1
            else:
                self.underCnt = 0

            if self.underCnt >= self.maxUnder:
                self.mu = est + runInfo.mss/runInfo.lastRTT
            if est < self.mu:
                self.mu = (self.mu + est)/2
            else:
                self.mu += runInfo.mss/runInfo.lastRTT


            self.reset(runInfo)

            self.mu = max(runInfo.mss/runInfo.lastRTT, self.mu)
        else:
            self.integ += rate*dt
            self.totalTime += dt


class PY_MPCC:
    def __init__(self, runInfo, mu, target_rtt, maxMUUnder):
        self.mu = mu
        self.target_rtt = target_rtt

        self.alpha = 0.0

        self.minRate = runInfo.mss/runInfo.lastRTT

        self.bdp = 1
        self._cwnd = 1
        self.ssthresh = 2*self.mu*runInfo.lastRTT/runInfo.mss

        self.mrtt = runInfo.lastRTT
        self.lastTime = runInfo.time
        self.predRTT = self.mrtt
        self.err = 0
        self.rate = 2*self.mu

        self.muEst = MUEst(runInfo, maxMUUnder, self.rate)


    def pacingRate(self, runInfo):
        return self.rate

    def cwnd(self, runInfo):
        return self._cwnd


    def ack(self, runInfo):
        self.updateAlpha(runInfo)
        self.updateMinRate(runInfo)

        rtt = runInfo.lastRTT
        self.mrtt = self.wma(self.mrtt, rtt)


        if self.inSlowStart():
            if self.mrtt > self.target_rtt:
                self.loss(runInfo)
            elif runInfo.time > self.lastTime + self.target_rtt:
                self.lastTime = runInfo.time

                self.bdp = self._cwnd
                self._cwnd *= 2
                self.rate = 2*self._cwnd*runInfo.mss/self.target_rtt
        elif runInfo.time > self.lastTime + self.target_rtt:
            self.muEst.update(runInfo, self.rate)

            self.lastTime = runInfo.time

            t = self.target_rtt
            w = self.target_rtt**2/self.mu**2

            a = 0.9
            ref = a*self.mrtt + (1 - a)*self.target_rtt

            mu = self.muEst.get()
            self.err = a*self.err + (1 - a)*(self.mrtt - self.predRTT)

            num = t*(t - self.err + ref - self.mrtt) + w*mu*self.rate
            den = t**2 + w*mu**2
            self.rate = num/den*mu

            self.predRTT = self.mrtt + t*(self.rate - mu)/mu

            self.bdp = self.rate*self.target_rtt/runInfo.mss
            self._cwnd = 2*self.bdp

            if self.mrtt > self.target_rtt:
                self.ssthresh = min(self.ssthresh, self.bdp/2)


        self._cwnd = max(1, self._cwnd)
        self.rate = min(max(self.rate, self.minRate), 2*self.mu)


    def loss(self, runInfo):
        self._cwnd = self.bdp*self.target_rtt/runInfo.lastRTT
        self.ssthresh = self._cwnd/2

        self.rate = self._cwnd*runInfo.mss/self.target_rtt
        self.muEst.hardReset(runInfo, self.rate)

        self._cwnd = max(1, self._cwnd)
        self.rate = min(max(self.rate, self.minRate), 2*self.mu)


    def inSlowStart(self):
        return self._cwnd < self.ssthresh


    def getDebugInfo(self):
        return {'mrtt': self.mrtt,
                'mu': self.muEst.get(),
                'err': self.err,
                'ssthresh': self.ssthresh}


    def wma(self, avg, x):
        return self.alpha*avg + (1 - self.alpha)*x

    def updateAlpha(self, runInfo):
        self.alpha = 0.9*(1 - 1/max(1, runInfo.inflight))

    def updateMinRate(self, runInfo):
        self.minRate = runInfo.mss/self.mrtt
