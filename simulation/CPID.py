
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
        info.delivered = round(runInfo.delivered)
        info.inflight = round(runInfo.inflight)
        info.mss = round(runInfo.mss)
        info.hops = round(runInfo.hops)
    else:
        info.time = runInfo.time*_pid.lib.US_PER_SEC
        info.lastRTT = runInfo.lastRTT*_pid.lib.US_PER_SEC
        info.delivered = runInfo.delivered
        info.inflight = runInfo.inflight
        info.mss = runInfo.mss
        info.hops = runInfo.hops

    return info

class CPID:
    def __init__(self, runInfo, bottleneckRate, baseRTT, rttGain, maxFlows):
        cfg = _pid.ffi.new("struct pid_config*")

        if _pid.ffi.typeof('SNum').cname == 'int64_t':
            cfg.bottleneckRate = int(bottleneckRate)
            cfg.baseRTT = int(baseRTT*_pid.lib.US_PER_SEC)
            cfg.rttGain = int(rttGain*_pid.lib.US_PER_SEC)
            cfg.maxFlows = int(maxFlows)
        else:
            cfg.bottleneckRate = bottleneckRate
            cfg.baseRTT = baseRTT*_pid.lib.US_PER_SEC
            cfg.rttGain = rttGain
            cfg.rttFlows = maxFlows

        self.p = _pid.ffi.new("struct pid_control*")
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
        return {'srtt': self.p.srtt/_pid.lib.US_PER_SEC,
                'tau': self.p.tau/_pid.lib.US_PER_SEC,
                'mu': self.p.mu,
                'integ': self.p.integ,
                'slowStart': int(self.p.slowStart),
                'targetRTT': self.p.targetRTT/_pid.lib.US_PER_SEC}
