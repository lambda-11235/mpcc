
import numpy.random as npr

import _mpcc



class RuntimeInfo:
    def __init__(self, time, lastRTT, delivered, inflight, mss, hops):
        self.time = time
        self.lastRTT = lastRTT
        self.delivered = delivered
        self.inflight = inflight
        self.mss = mss
        self.hops = hops


class CongControl:
    def pacingRate(self, runInfo):
        return 1.0

    def cwnd(self, runInfo):
        """
        Return 0 for unlimited.
        """
        return 0

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


class AIMD:
    def __init__(self, runInfo, mu, targetRTT):
        self.mu = mu
        self.targetRTT = targetRTT
        self.minInc = min(1, 1.0e-3*self.mu*self.targetRTT/runInfo.mss)

        self.mrtt = runInfo.lastRTT
        self.lastTime = runInfo.time

        self._cwnd = 1
        self.ssthresh = mu*targetRTT/runInfo.mss

    def pacingRate(self, runInfo):
        if self._cwnd > 1:
            return self.mu
        else:
            return self._cwnd*runInfo.mss/self.targetRTT

    def cwnd(self, runInfo):
        if self._cwnd > 1:
            return self._cwnd
        else:
            return 1

    def ack(self, runInfo):
        self.minInc = min(1, 1.0e-3*self.mu*self.targetRTT/runInfo.mss)
        self.mrtt = 0.9*self.mrtt + 0.1*runInfo.lastRTT

        if self._cwnd < self.ssthresh:
            if self.mrtt < self.targetRTT:
                self._cwnd += 1
                self._cwnd = min(self._cwnd, self.ssthresh + 1)
            else:
                self.ssthresh = self._cwnd/2
                self.lastTime = runInfo.time
        elif self.lastTime + self.targetRTT < runInfo.time:
            if self.mrtt < self.targetRTT:
                self._cwnd += self.minInc
            else:
                self._cwnd *= self.targetRTT/self.mrtt

            self.lastTime = runInfo.time

        self._cwnd = max(self.minInc, self._cwnd)

    def loss(self, runInfo):
        self._cwnd /= 2
        self._cwnd = max(self.minInc, self._cwnd)

        self.ssthresh = self._cwnd - 1

    def getDebugInfo(self):
        return {'ssthresh': self.ssthresh, 'mrtt': self.mrtt}
