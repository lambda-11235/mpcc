
import numpy as np
import numpy.random as npr

from CC import *


class PY_MPCC:
    def __init__(self, runInfo, mu, target_rtt, w, maxRBUnder):
        self.mu = mu
        self.target_rtt = target_rtt
        self.maxRBUnder = maxRBUnder

        self.alpha = 0.0
        self.w = w

        self.minRate = runInfo.mss/runInfo.lastRTT

        self._cwnd = 1
        self.ssthresh = self.mu*runInfo.lastRTT/runInfo.mss

        self.mrtt = runInfo.lastRTT
        self.lastTime = runInfo.time
        self.rate = self.mu

        self.resetRTTEst(runInfo)
        self.rbUnderCnt = 0
        self.rb = self.rate
        #self.rb = npr.exponential(self.mu)


    def pacingRate(self, runInfo):
        return self.rate

    def cwnd(self, runInfo):
        return self._cwnd


    def ack(self, runInfo):
        self.updateAlpha(runInfo)
        self.updateMinRate(runInfo)

        rtt = runInfo.lastRTT
        self.mrtt = self.wma(self.mrtt, rtt)

        dt = runInfo.time - self.lastTime
        self.lastTime = runInfo.time

        self.rbComp(runInfo, dt)


        if self.inSlowStart():
            if self.mrtt > self.target_rtt:
                self.loss(runInfo)
            else:
                self._cwnd += 1
                self.rate = self.mu
        else:
            t = (1 + self.w)*self.target_rtt
            num = t + (self.target_rtt - self.mrtt)
            den = t
            self.rate = self.rb*num/den

            bdp = self.rate*self.target_rtt/runInfo.mss
            self._cwnd = 2*bdp


        self.rate = min(max(self.rate, self.minRate), self.mu)


    def rbComp(self, runInfo, dt):
        if self.rbTime > self.mrtt:
            rbEst = self.rbInteg/(self.rbTime + self.mrtt - self.rbRTT)

            # Note that rbUnderCnt implementation is slightly
            # different than for PID.  This bacause we use rb to
            # directly compute the rate in MPCC, while for PID it
            # mostly accelerates convergence.
            if self.rb < rbEst:
                self.rbUnderCnt += 1
            else:
                self.rbUnderCnt = 0

            if self.rbUnderCnt >= self.maxRBUnder:
                self.rb = rbEst
            if rbEst < self.rb:
                self.rb = (self.rb + rbEst)/2
            else:
                self.rb += self.minRate

            self.resetRTTEst(runInfo)

            self.rb = max(self.minRate, self.rb)
        else:
            self.rbInteg += self.rate*dt
            self.rbTime += dt


    def loss(self, runInfo):
        self._cwnd /= 2
        self.ssthresh = self._cwnd

        rbEst = runInfo.inflight*runInfo.mss/runInfo.lastRTT
        self.rb = rbEst
        self.rate = self.rb

        self.resetRTTEst(runInfo)


    def inSlowStart(self):
        return self._cwnd < self.ssthresh

    def resetRTTEst(self, runInfo):
        self.rbRTT = self.mrtt
        self.rbInteg = 0
        self.rbTime = 0


    def getDebugInfo(self):
        return {'mrtt': self.mrtt, 'rb': self.rb, 'ssthresh': self.ssthresh}


    def wma(self, avg, x):
        return self.alpha*avg + (1 - self.alpha)*x

    def updateAlpha(self, runInfo):
        self.alpha = 0.9*(1 - 1/max(1, runInfo.inflight))

    def updateMinRate(self, runInfo):
        self.minRate = runInfo.mss/self.mrtt
