
import numpy as np
import numpy.random as npr

import math

from CC import *
import _pid


def convertRunInfo(runInfo):
    info = _pid.ffi.new("struct runtime_info*")

    if _pid.ffi.typeof('SNum').cname == 'int64_t':
        info.time = round(runInfo.time*_pid.lib.US_PER_SEC)
        info.lastRTT = round(runInfo.lastRTT*_pid.lib.US_PER_SEC)
        info.inflight = round(runInfo.inflight)
        info.mss = round(runInfo.mss)
    else:
        info.time = runInfo.time*_pid.lib.US_PER_SEC
        info.lastRTT = runInfo.lastRTT*_pid.lib.US_PER_SEC
        info.inflight = runInfo.inflight
        info.mss = runInfo.mss

    return info

class CPID:
    def __init__(self, runInfo, bottleneckRate, targetRTT):
        cfg = _pid.ffi.new("struct pid_config*")

        if _pid.ffi.typeof('SNum').cname == 'int64_t':
            cfg.bottleneckRate = int(bottleneckRate)
            cfg.targetRTT = int(targetRTT*_pid.lib.US_PER_SEC)
        else:
            cfg.bottleneckRate = bottleneckRate
            cfg.targetRTT = targetRTT*_pid.lib.US_PER_SEC

        self.p = _pid.ffi.new("struct pid*")
        _pid.lib.pid_init(self.p, cfg, convertRunInfo(runInfo))

    def pacingRate(self, runInfo):
        return _pid.lib.pid_pacing_rate(self.p, convertRunInfo(runInfo))

    def cwnd(self, runInfo):
        return _pid.lib.pid_cwnd(self.p, convertRunInfo(runInfo))

    def ack(self, runInfo):
        _pid.lib.pid_on_ack(self.p, convertRunInfo(runInfo))

    def loss(self, runInfo):
        _pid.lib.pid_on_loss(self.p, convertRunInfo(runInfo))

    def getDebugInfo(self):
        return {'mrtt': self.p.mrtt/_pid.lib.US_PER_SEC,
                'devRTT':self.p.devRTT/_pid.lib.US_PER_SEC,
                'mu': self.p.mu,
                'integ': self.p.integ}
