
#include "pid.h"


void pid_update(struct pid_control *self, struct runtime_info *info);
void pid_update_rate(struct pid_control *self, struct runtime_info *info);
void pid_update_srtt(struct pid_control *self, struct runtime_info *info);
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

SNum pid_div(SNum x, SNum y) {
    if (y == 0) {
        #ifdef PID_KERNEL_MODE
        printk("pid_cc: Division by zero, %lld/%lld\n", x, y);
        #endif

        return x;
    } else {
        return x/y;
    }
}

SNum pid_sqr(SNum x) {
    return x*x;
}

SNum pid_wma(SNum avg, SNum x) {
    return (9*avg + x)/10;
}

SNum pid_log2(SNum x) {
    SNum res = 0;

    while (x > 1) {
        res += 1;
        x >>= 1;
    }

    return res;
}

SNum pid_sqrt(SNum x) {
    SNum res = x;
    SNum i;

    for(i = 0; i < 16; i++)
        res = (res + x/res)/2;

    return res;
}



void pid_init(struct pid_control *self, const struct pid_config *cfg, struct runtime_info *info) {
    self->cfg = *cfg;
    pid_reset(self, info);
}


void pid_release(struct pid_control *self) {
}


void pid_reset(struct pid_control *self, struct runtime_info *info) {
    self->minRate = pid_max(minDelta,
                            self->cfg.bottleneckRate/(2*self->cfg.maxFlows));

    self->srtt = info->lastRTT;
    self->hpRTT = info->lastRTT;
    self->srttLastTime = info->time;

    self->tau = pid_max(4*self->cfg.baseRTT,
                        pid_div(info->mss*US_PER_SEC, self->cfg.bottleneckRate));

    self->targetRTT = self->cfg.baseRTT
        + pid_div(info->hops*info->mss, self->minRate);

    self->rateLastTime = info->time;
    self->targetLastTime = info->time;

    self->integ = self->minRate;
    self->rate = self->integ;
    self->slowStart = true;

    self->mu = self->cfg.bottleneckRate;
    self->goodput = self->minRate;
    self->gputDeliv = 0;
    self->gputTime = info->time;
}



SNum pid_pacing_rate(struct pid_control *self, struct runtime_info *info) {
    return self->rate;
}


SNum pid_cwnd(struct pid_control *self, struct runtime_info *info) {
    SNum bdp;

    if (info->mss < 1)
        bdp = self->cfg.bottleneckRate*self->targetRTT/US_PER_SEC;
    else
        bdp = pid_div(self->cfg.bottleneckRate*self->targetRTT, info->mss*US_PER_SEC);

    return pid_max(4, bdp);
}


void pid_on_ack(struct pid_control *self, struct runtime_info *info) {
    SNum deliv, est;

    //self->minRate = pid_min(self->cfg.bottleneckRate/128,
    //                        pid_div(info->mss*US_PER_SEC, self->srtt));
    //self->minRate = pid_max(minDelta, self->minRate);

    pid_update_srtt(self, info);


    if (self->srtt > self->targetRTT)
        self->slowStart = false;
    

    deliv = info->delivered - self->gputDeliv;
    if (info->time > self->gputTime + self->targetRTT && deliv > 0) {
        est = pid_div(deliv*info->mss*US_PER_SEC, info->time - self->gputTime);

        if (self->srtt > self->targetRTT)
            self->mu = est;
        else
            self->mu = pid_max(self->mu, est);

        self->goodput = pid_clamp(est, self->minRate, self->cfg.bottleneckRate);
        self->mu = pid_clamp(self->mu, self->minRate, 2*self->cfg.bottleneckRate);

        self->gputDeliv = info->delivered;
        self->gputTime = info->time;
    }


    pid_update(self, info);
}


void pid_on_loss(struct pid_control *self, struct runtime_info *info) {
    SNum dt, diffInteg;

    dt = info->time - self->rateLastTime;

    if (dt < 1)
        return;

    diffInteg = pid_div((self->minRate - self->rate)*pid_min(self->tau, dt), self->tau);

    if (diffInteg != 0) {
        self->rateLastTime = info->time;

        self->integ += diffInteg;
        self->rate = self->integ;
    }

    self->integ = pid_clamp(self->integ, self->minRate, 2*self->cfg.bottleneckRate);
    self->rate = pid_clamp(self->rate, self->minRate, 2*self->cfg.bottleneckRate);
}


void pid_update(struct pid_control *self, struct runtime_info *info) {
    pid_update_targetRTT(self, info);
    pid_update_rate(self, info);
}


void pid_update_rate(struct pid_control *self, struct runtime_info *info) {
    SNum dt, err;
    SNum kpNum, kpDen, kiNum, kiDen;
    SNum diffInteg;

    dt = info->time - self->rateLastTime;

    if (dt < 1)
        return;

    err = self->targetRTT - info->lastRTT;

    kpNum = 2*self->mu;
    kpDen = self->tau;

    kiNum = self->mu;
    kiDen = pid_sqr(self->tau);

    if (self->slowStart) {
        diffInteg = pid_div(self->rate*pid_min(self->tau, dt), self->tau);
    } else {
        diffInteg = pid_div(kiNum*err*pid_min(self->tau, dt), kiDen);
    }

    if (diffInteg != 0) {
        self->rateLastTime = info->time;

        self->integ += diffInteg;
        self->rate = pid_div(kpNum*err, kpDen) + self->integ;
    }

    self->integ = pid_clamp(self->integ, self->minRate, 2*self->cfg.bottleneckRate);
    self->rate = pid_clamp(self->rate, self->minRate, 2*self->cfg.bottleneckRate);
}


void pid_update_srtt(struct pid_control *self, struct runtime_info *info) {
    SNum dt;
    SNum diffSRTT;
    SNum diffHP;

    dt = info->time - self->srttLastTime;

    if (dt < 1)
        return;

    diffSRTT = info->lastRTT - self->srtt;
    diffSRTT = pid_div(diffSRTT*pid_min(self->cfg.baseRTT, dt), self->cfg.baseRTT);

    diffHP = pid_div(self->hpRTT*pid_max(0, self->tau - dt), self->tau) - self->hpRTT;
    diffHP = pid_max(diffHP, info->lastRTT - self->hpRTT);

    if (diffSRTT != 0) {
        self->srttLastTime = info->time;

        self->srtt += diffSRTT;
        self->hpRTT += diffHP;

        self->srtt = pid_max(minDelta, self->srtt);
    }

    self->tau = 2*self->srtt + 2*info->mss*US_PER_SEC/self->mu;
}


void pid_update_targetRTT(struct pid_control *self, struct runtime_info *info) {
    SNum dt, nt;
    SNum diffTargetRTT;
    SNum gmean = self->rate;
    int i;

    for (i = 0; i < 10; i++)
        gmean = (gmean + self->rate*(self->cfg.bottleneckRate/gmean))/2;

    dt = info->time - self->targetLastTime;

    if (dt < 1 || gmean < 1)
        return;

    nt = self->cfg.baseRTT;
    nt += self->cfg.rttGain*pid_div(self->cfg.bottleneckRate, self->goodput);
    nt += self->cfg.rttGain*info->hops;

    diffTargetRTT = pid_div((nt - self->targetRTT)*pid_min(self->tau, dt), self->tau);


    if (diffTargetRTT != 0) {
        self->targetLastTime = info->time;

        self->targetRTT += diffTargetRTT;
    }

    self->targetRTT = pid_max(self->cfg.baseRTT, self->targetRTT);
}
