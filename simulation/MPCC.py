
import numpy as np
import numpy.random as npr

import math

from CC import *
import _mpcc


def convertRunInfo(runInfo):
    info = _mpcc.ffi.new("struct runtime_info*")

    if _mpcc.ffi.typeof('SNum').cname == 'int64_t':
        info.time = math.ceil(runInfo.time*_mpcc.lib.US_PER_SEC)
        info.lastRTT = math.ceil(runInfo.lastRTT*_mpcc.lib.US_PER_SEC)
        info.inflight = math.ceil(runInfo.inflight)
        info.mss = math.ceil(runInfo.mss)
    else:
        info.time = runInfo.time*_mpcc.lib.US_PER_SEC
        info.lastRTT = runInfo.lastRTT*_mpcc.lib.US_PER_SEC
        info.inflight = runInfo.inflight
        info.mss = runInfo.mss

    return info

class MPCC:
    def __init__(self, runInfo, bottleneckRate, targetRTT):
        cfg = _mpcc.ffi.new("struct mpcc_config*")
        cfg.bottleneckRate = int(bottleneckRate)
        cfg.targetRTT = int(targetRTT*_mpcc.lib.US_PER_SEC)

        self.m = _mpcc.ffi.new("struct mpcc*")
        _mpcc.lib.mpcc_init(self.m, cfg, convertRunInfo(runInfo))

    def pacingRate(self, runInfo):
        return _mpcc.lib.mpcc_pacing_rate(self.m, convertRunInfo(runInfo))

    def cwnd(self, runInfo):
        return _mpcc.lib.mpcc_cwnd(self.m, convertRunInfo(runInfo))

    def ack(self, runInfo):
        _mpcc.lib.mpcc_on_ack(self.m, convertRunInfo(runInfo))

    def loss(self, runInfo):
        _mpcc.lib.mpcc_on_loss(self.m, convertRunInfo(runInfo))

    def getDebugInfo(self):
        return {'mrtt': self.m.mrtt/_mpcc.lib.US_PER_SEC,
                'mu': self.m.mu,
                'err': self.m.err/_mpcc.lib.US_PER_SEC,
        #        'rtt_ref': self.ref,
                'ssthresh': self.m.ssthresh}
