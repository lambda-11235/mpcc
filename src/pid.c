
#include "pid.h"


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



void pid_init(struct pid *self, const struct pid_config *cfg, struct runtime_info *info) {
    self->cfg = *cfg;
    pid_reset(self, info);
}


void pid_release(struct pid *self) {
}


void pid_reset(struct pid *self, struct runtime_info *info) {
        self->minRate = pid_max(minDelta, info->mss*US_PER_SEC/info->lastRTT);
        self->minRTT = info->lastRTT;

        self->mrtt = info->lastRTT;
        self->devRTT = 0;
        self->lastTime = info->time;

        self->integ = self->minRate;
        self->lastErr = 0;
        self->rate = self->minRate;

        self->mu = self->cfg.bottleneckRate;
        self->muACKed = 0;
        self->muTime = info->time;
}



SNum pid_pacing_rate(struct pid *self, struct runtime_info *info) {
    //printf("%f\n", (double) self->rate/(double) self->cfg.bottleneckRate);
    return self->rate;
}


SNum pid_cwnd(struct pid *self, struct runtime_info *info) {
    //printf("%ld\n", self->_cwnd);
    return pid_max(1, 2*self->rate*self->mrtt/(info->mss*US_PER_SEC));
}


void pid_on_ack(struct pid *self, struct runtime_info *info) {
    SNum dt, err, est, tau, upper;
    SNum kpNum, kpDen, kiNum, kiDen;
    SNum integDelta;

    self->minRate = pid_max(minDelta, info->mss*US_PER_SEC/self->cfg.targetRTT);
    self->minRTT = pid_min(self->minRTT, info->lastRTT);

    if (info->inflight < 8)
        self->mrtt = info->lastRTT;
    else
        self->mrtt = pid_wma(self->mrtt, info->lastRTT);

    self->devRTT = pid_wma(self->devRTT, pid_abs(info->lastRTT - self->mrtt));


    self->muACKed += 1;
    if (info->time > self->muTime + self->cfg.targetRTT) {
        est = self->muACKed*info->mss*US_PER_SEC/(info->time - self->muTime);

        if (self->mrtt > self->cfg.targetRTT)
            self->mu = est;
        else
            self->mu = pid_max(self->mu, est);

        self->mu = pid_clamp(self->mu, self->minRate, 2*self->cfg.bottleneckRate);

        self->muACKed = 0;
        self->muTime = info->time;
    }


    err = self->cfg.targetRTT - self->mrtt;
    tau = 4*self->cfg.targetRTT;

    if (self->mrtt < self->cfg.targetRTT - 8*self->devRTT) {
        upper = self->cfg.targetRTT - US_PER_SEC*info->inflight*info->mss/self->mu;
        err = pid_max(err, upper);
    }


    kpNum = 2*self->mu;
    kpDen = tau;

    kiNum = self->mu;
    kiDen = pid_sqr(tau);

    dt = info->time - self->lastTime;
    integDelta = kiNum*err*dt/kiDen;
    //printf("%ld = %ld*%ld*%ld/%ld\n", integDelta, kiNum, err, dt, kiDen);

    if (pid_abs(integDelta) > 0) {
        self->integ += integDelta;
        self->integ += self->minRate*dt/tau/10;

        self->rate = kpNum*err/kpDen + self->integ;
        self->lastTime = info->time;
    }

    self->integ = pid_clamp(self->integ, self->minRate, 2*self->cfg.bottleneckRate);
    self->rate = pid_clamp(self->rate, self->minRate, 2*self->cfg.bottleneckRate);
}


void pid_on_loss(struct pid *self, struct runtime_info *info) {
    self->integ = self->mu/2;
    self->rate = self->minRate;
}
