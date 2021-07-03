
import numpy as np
import numpy.random as npr

from CC import *
import _mpcc


def convertRunInfo(runInfo):
    info = _mpcc.ffi.new("struct runtime_info*")

    if _mpcc.ffi.typeof('SNum').cname == 'int64_t':
        info.time = np.ceil(runInfo.time)
        info.lastRTT = np.ceil(runInfo.lastRTT)
        info.inflight = np.ceil(runInfo.inflight)
        info.mss = np.ceil(runInfo.mss)
    else:
        info.time = runInfo.time
        info.lastRTT = runInfo.lastRTT
        info.inflight = runInfo.inflight
        info.mss = runInfo.mss

    return info

class MPCC:
    def __init__(self, runInfo, bottleneckRate, targetRTT):
        cfg = _mpcc.ffi.new("struct mpcc_config*")
        cfg.bottleneckRate = int(bottleneckRate)
        cfg.targetRTT = int(targetRTT)

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
        return {'mrtt': self.m.mrtt*self.m.cfg.targetRTT/_mpcc.lib.M,
                'mu': self.m.mu*self.m.cfg.bottleneckRate/_mpcc.lib.M,
                'err': self.m.err*self.m.cfg.targetRTT/_mpcc.lib.M,
        #        'rtt_ref': self.ref,
                'ssthresh': self.m.ssthresh*self.m.cfg.bottleneckRate/_mpcc.lib.M}
