
import numpy as np
import numpy.random as npr

from CC import *


class PID:
    def __init__(self, runInfo, mu, target_rtt, m):
        self.mu = mu
        self.target_rtt = target_rtt
        self.m = m

        self.alpha = 0.0

        self.mrtt = runInfo.lastRTT
        self.lastTime = runInfo.time
        self.minRate = runInfo.mss/runInfo.lastRTT

        self._cwnd = 1
        self.ssthresh = self.mu*runInfo.lastRTT/runInfo.mss

        self.rate = self.mu
        #self.rate = npr.uniform(self.minRate, self.mu/4)

        self.rbInteg = 0
        self.rbTime = 0
        self.rb = self.rate

        self.integ = self.rate/self.ki()


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


        if self.inSlowStart():
            if self.mrtt > self.target_rtt:
                self.ssthresh = self._cwnd/2

                self.rb = runInfo.inflight*runInfo.mss/self.mrtt
                self.rbInteg = 0
                self.rbTime = 0

                self.rate = self.rb
                self.integ = self.rb/self.ki()
            else:
                self._cwnd += 1
        else:
            if self.rbTime > self.mrtt:
                rbEst = self.rbInteg/self.rbTime

                if rbEst < self.rb:
                    self.rb = (self.rb + rbEst)/2
                else:
                    self.rb += self.minRate

                self.rbInteg = 0
                self.rbTime = 0

                self.rb = max(self.minRate, self.rb)
            else:
                self.rbInteg += runInfo.inflight/self.mrtt*dt
                self.rbTime += dt


            err = self.target_rtt - self.mrtt + self.rb - self.rate

            self.integ += err*dt
            self.integ = min(max(0, self.integ), 2*self.mu/self.ki())

            dedt = err/dt
            self.rate = self.kp()*err + self.ki()*self.integ + self.kd()*dedt

            self._cwnd = 2*self.rate*self.mrtt/runInfo.mss

        self._cwnd = max(1, self._cwnd)
        self.rate = min(max(self.rate, self.minRate), 2*self.mu)


    def kp(self): return 2*self.rb/(self.m*self.target_rtt)
    def ki(self): return self.kp()**2/(4*self.rb)
    def kd(self): return 0


    def loss(self, runInfo):
        self.rate = self.minRate

    def inSlowStart(self):
        return self._cwnd < self.ssthresh

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
        self.minRate = self.mu/1024
        #self.minRate = min(self.mu/128, runInfo.mss/self.mrtt)
