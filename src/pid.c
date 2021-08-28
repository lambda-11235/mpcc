
#include "pid.h"


void pid_update(struct pid_control *self, struct runtime_info *info);
void pid_update_rate(struct pid_control *self, struct runtime_info *info);
void pid_update_targetRTT(struct pid_control *self, struct runtime_info *info);


SNum pid_abs(SNum x) {
    if (x < 0)
        return -x;
    else
        return x;
}

SNum pid_min(SNum x, SNum y) {
    if (x < y)
        return x;
    else
        return y;
}

SNum pid_max(SNum x, SNum y) {
    if (x > y)
        return x;
    else
        return y;
}

SNum pid_clamp(SNum x, SNum min, SNum max) {
    if (x < min)
        return min;
    else if (x > max)
        return max;
    else
        return x;
}

SNum pid_sqr(SNum x) {
    return x*x;
}

SNum pid_wma(SNum avg, SNum x) {
    return (9*avg + x)/10;
}



void pid_init(struct pid_control *self, const struct pid_config *cfg, struct runtime_info *info) {
    self->cfg = *cfg;
    pid_reset(self, info);
}


void pid_release(struct pid_control *self) {
}


void pid_reset(struct pid_control *self, struct runtime_info *info) {
    self->minRate = pid_min(self->cfg.bottleneckRate/128,
                            info->mss*US_PER_SEC/self->cfg.baseRTT);
    self->minRate = pid_max(minDelta, self->minRate);

    self->minRTT = info->lastRTT;

    self->targetRTT = self->cfg.baseRTT
        + info->hops*info->mss/self->minRate;

    self->mrtt = info->lastRTT;
    self->devRTT = 0;

    self->rateLastTime = info->time;
    self->rttLastTime = info->time;

    self->integ = self->minRate;
    self->rate = self->minRate;
    self->ssthresh = self->cfg.bottleneckRate;

    self->mu = self->cfg.bottleneckRate;
    self->muDeliv = 0;
    self->muTime = info->time;
}



SNum pid_pacing_rate(struct pid_control *self, struct runtime_info *info) {
    return self->rate;
}


SNum pid_cwnd(struct pid_control *self, struct runtime_info *info) {
    SNum bdp = self->rate*self->targetRTT/(info->mss*US_PER_SEC);
    return 1 + bdp;
}


void pid_on_ack(struct pid_control *self, struct runtime_info *info) {
    SNum deliv, est;

    self->minRate = pid_min(self->cfg.bottleneckRate/128,
                            info->mss*US_PER_SEC/self->targetRTT);
    self->minRate = pid_max(minDelta, self->minRate);

    self->minRTT = pid_min(self->minRTT, info->lastRTT);

    if (info->inflight < 8)
        self->mrtt = info->lastRTT;
    else
        self->mrtt = pid_wma(self->mrtt, info->lastRTT);

    self->devRTT = pid_wma(self->devRTT, pid_abs(info->lastRTT - self->mrtt));


    deliv = info->delivered - self->muDeliv;
    if (info->time > self->muTime + self->targetRTT && deliv >= 4) {
        est = deliv*info->mss*US_PER_SEC/(info->time - self->muTime);

        if (self->mrtt > self->targetRTT)
            self->mu = est;
        else
            self->mu = pid_max(self->mu, est);

        self->mu = pid_clamp(self->mu, self->minRate, 2*self->cfg.bottleneckRate);

        self->muDeliv = info->delivered;
        self->muTime = info->time;
    }


    if (self->mrtt > self->targetRTT) {
        self->ssthresh = self->mu/2;
    }

    pid_update(self, info);
}


void pid_on_loss(struct pid_control *self, struct runtime_info *info) {
    self->ssthresh = pid_min(self->ssthresh, self->mu/2);
    pid_update(self, info);
}


void pid_update(struct pid_control *self, struct runtime_info *info) {
    pid_update_rate(self, info);
    pid_update_targetRTT(self, info);
}


void pid_update_rate(struct pid_control *self, struct runtime_info *info) {
    SNum dt, err, tau;
    SNum kpNum, kpDen, kiNum, kiDen;
    SNum diffInteg;

    err = self->targetRTT - self->mrtt;
    tau = pid_max(4*self->targetRTT, info->mss*US_PER_SEC/self->mu);

    kpNum = 2*self->mu;
    kpDen = tau;

    kiNum = self->mu;
    kiDen = pid_sqr(tau);

    dt = info->time - self->rateLastTime;

    if (self->rate < self->ssthresh)
        diffInteg = self->rate*dt/tau;
    else
        diffInteg = kiNum*err*dt/kiDen;

    if (diffInteg != 0) {
        self->rateLastTime = info->time;

        self->integ += diffInteg;
        self->rate = kpNum*err/kpDen + self->integ;

        self->integ = pid_clamp(self->integ, self->minRate, 2*self->cfg.bottleneckRate);
        self->rate = pid_clamp(self->rate, self->minRate, 2*self->cfg.bottleneckRate);
    }
}


void pid_update_targetRTT(struct pid_control *self, struct runtime_info *info) {
    SNum dt, nt, tau;
    SNum diffTargetRTT;

    tau = pid_max(4*self->targetRTT, info->mss*US_PER_SEC/self->mu);
    dt = info->time - self->rttLastTime;

    nt = self->cfg.baseRTT;
    nt += info->hops*info->mss*US_PER_SEC/self->cfg.bottleneckRate;
    nt += info->mss*US_PER_SEC/self->mu;
    diffTargetRTT = (nt - self->targetRTT)*dt/tau;


    if (diffTargetRTT != 0) {
        self->rttLastTime = info->time;

        self->targetRTT += diffTargetRTT;
        self->targetRTT = pid_max(self->cfg.baseRTT, self->targetRTT);
    }
}
