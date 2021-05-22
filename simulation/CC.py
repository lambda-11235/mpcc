
import numpy.random as npr

import _mpcc



class RuntimeInfo:
    def __init__(self, time, lastRTT, inflight, mss):
        self.time = time
        self.lastRTT = lastRTT
        self.inflight = inflight
        self.mss = mss


class CongControl:
    def pacingRate(self, runInfo):
        return 1.0
    
    def cwnd(self, runInfo):
        return 1

    def ack(self, runInfo):
        pass
    
    def loss(self, runInfo):
        pass

    def getDebugInfo(self):
        return {}


class ExactCC:
    def __init__(self, pacingRate, cwnd):
        self._pacingRate = pacingRate
        self._cwnd = cwnd
        
    def pacingRate(self, runInfo):
        return self._pacingRate
    
    def cwnd(self, runInfo):
        return self._cwnd

    def ack(self, runInfo):
        pass
    
    def loss(self, runInfo):
        pass

    def getDebugInfo(self):
        return {}



class PY_MPCC:
    def __init__(self, runInfo, mu, target_rtt, w):
        self.mu = mu
        self.target_rtt = target_rtt

        self.alpha = 0.0
        self.w = w

        self.minRate = runInfo.mss/runInfo.lastRTT

        self.mrtt = runInfo.lastRTT
        self.lastTime = runInfo.time
        self.rate = self.minRate

        self.ssthresh = 10*mu
        self.resetRTTEst(runInfo)

        self.rb = self.minRate
        #self.rb = npr.exponential(G.MU/G.NUM_CLIENTS/2)


    def pacingRate(self, runInfo):
        return self.rate
    
    def cwnd(self, runInfo):
        return 2*self.rate*self.target_rtt/runInfo.mss

    
    def ack(self, runInfo):
        self.updateAlpha(runInfo)
        self.updateMinRate(runInfo)

        rtt = runInfo.lastRTT
        self.mrtt = self.wma(self.mrtt, rtt)

        dt = runInfo.time - self.lastTime
        self.lastTime = runInfo.time

        self.rbComp(runInfo, dt)
        
        t = self.mrtt/2
        num = self.target_rtt - self.mrtt + (1 + self.w)*t
        den = (1 + self.w)*t
        r = self.rb*num/den
        self.rate = r

        self.rate = min(max(self.rate, self.minRate), self.mu)

        
    def rbComp(self, runInfo, dt):
        if self.rb < self.ssthresh and self.mrtt > self.target_rtt:
            self.loss(runInfo)
        elif self.rbTime > self.mrtt and self.rbInteg > 0:
            rbEst = self.rbInteg/(self.mrtt - self.rbRTT + self.rbTime)

            if self.rb < self.ssthresh:
                self.rb = min(2*rbEst, self.ssthresh) + self.minRate
            elif rbEst < self.rb:
                self.rb = (self.rb + rbEst)/2
            else:
                self.rb += self.minRate
            
            self.resetRTTEst(runInfo)
        else:
            self.rbInteg += self.rate*dt
            self.rbTime += dt

        self.rb = min(max(self.rb, self.minRate), self.mu)

    
    def loss(self, runInfo):
        rbEst = runInfo.inflight*runInfo.mss/self.mrtt
        self.rb = min(self.rb/2, rbEst)
        self.ssthresh = self.rb/2

        self.resetRTTEst(runInfo)


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
        self.minRate = self.mu/1024
        #self.minRate = min(self.mu/128, runInfo.mss/self.mrtt)
