
import numpy as np
import numpy.random as npr

from CC import *


class PID:
    def __init__(self, runInfo, mu, target_rtt, m, maxRBUnder):
        self.mu = mu
        self.target_rtt = target_rtt
        self.m = max(2, m)
        self.maxRBUnder = maxRBUnder

        self.alpha = 0.0

        self.mrtt = runInfo.lastRTT
        self.lastTime = runInfo.time
        self.minRate = runInfo.mss/runInfo.lastRTT

        self._cwnd = 1
        self.ssthresh = 2*self.mu*runInfo.lastRTT/runInfo.mss

        self.integ = 0
        self.rate = 2*self.mu
        #self.rate = npr.uniform(self.minRate, self.mu/4)

        self.resetRTTEst(runInfo)
        self.rbUnderCnt = 0
        self.rb = self.rate

        self.updateParams()


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


        self.updateRB(runInfo, dt)
        self.updateParams()


        if self.inSlowStart():
            if self.mrtt > self.target_rtt:
                self.loss(runInfo)
            else:
                self._cwnd += 1
                self.rate = 2*self.mu
        else:
            err = self.target_rtt - self.mrtt
            err += self.a*(self.rb - self.rate)

            self.integ += err*dt
            self.integ = min(max(0, self.integ), 2*self.mu/self.ki)

            dedt = err/dt
            self.rate = self.kp*err + self.ki*self.integ + self.kd*dedt

            self._cwnd = 2*self.rate*self.target_rtt/runInfo.mss

        self._cwnd = max(1, self._cwnd)
        self.rate = min(max(self.rate, self.minRate), 2*self.mu)


    def updateRB(self, runInfo, dt):
        if self.rbTime > self.mrtt:
            rbEst = self.rbInteg/(self.rbTime + self.mrtt - self.rbRTT)

            if self.rb < rbEst/2:
                self.rbUnderCnt += 1
            else:
                self.rbUnderCnt = 0

            if self.rbUnderCnt >= self.maxRBUnder:
                self.rb = rbEst/2
            if rbEst < self.rb:
                self.rb = (self.rb + rbEst)/2
            else:
                self.rb += self.minRate

            self.resetRTTEst(runInfo)

            self.rb = max(self.minRate, self.rb)
        else:
            self.rbInteg += self.rate*dt
            self.rbTime += dt


    def updateParams(self):
        tau = self.m*self.target_rtt

        self.a = self.target_rtt/self.mu
        den = max(0.1, (tau - self.a*self.rb)**2)
        self.kp = self.rb*(2*tau - self.a*self.rb)/den
        self.ki = self.rb/den

        #self.kp = 2*self.rb/(tau)
        #self.ki = self.kp**2/(4*self.rb)
        self.kd = 0


    def loss(self, runInfo):
        self._cwnd = runInfo.inflight*self.target_rtt/self.mrtt
        self.ssthresh = self._cwnd/2

        self.rate = self._cwnd*runInfo.mss/self.target_rtt
        self.integ = self.rate/self.ki

        self.rb = self.rate
        self.resetRTTEst(runInfo)


    def inSlowStart(self):
        return self._cwnd < self.ssthresh

    def resetRTTEst(self, runInfo):
        self.rbInteg = 0
        self.rbRTT = self.mrtt
        self.rbTime = 0


    def getDebugInfo(self):
        return {'mrtt': self.mrtt, 'integ': self.integ,
                'ssthresh': self.ssthresh,
                'rb': self.rb,
                'error': self.target_rtt - self.mrtt}


    def wma(self, avg, x):
        return self.alpha*avg + (1 - self.alpha)*x

    def updateAlpha(self, runInfo):
        self.alpha = 0.9*(1 - 1/max(1, runInfo.inflight))

    def updateMinRate(self, runInfo):
        self.minRate = min(self.mu/128, runInfo.mss/self.mrtt)
