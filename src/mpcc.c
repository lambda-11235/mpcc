
#include "mpcc.h"


SNum mpcc_abs(SNum x) {
    if (x < 0)
        return -x;
    else
        return x;
}

SNum mpcc_min(SNum x, SNum y) {
    if (x < y)
        return x;
    else
        return y;
}

SNum mpcc_max(SNum x, SNum y) {
    if (x > y)
        return x;
    else
        return y;
}

SNum mpcc_clamp(SNum x, SNum min, SNum max) {
    if (x < min)
        return min;
    else if (x > max)
        return max;
    else
        return x;
}

SNum mpcc_wma(SNum avg, SNum x) {
    return (9*avg + x)/10;
}



void mpcc_init(struct mpcc *m, const struct mpcc_config *cfg, struct runtime_info *info) {
    m->cfg = *cfg;
    mpcc_reset(m, info);
}


void mpcc_release(struct mpcc *m) {
}


void mpcc_reset(struct mpcc *m, struct runtime_info *info) {
    m->minRate = mpcc_max(minDelta, (info->mss*US_PER_SEC)/info->lastRTT);

    m->mrtt = info->lastRTT;
    m->devRTT = 0;
    m->lastTime = info->time;

    m->rate = m->minRate;

    m->mu = m->minRate;
    m->muDeliv = 0;
    m->muTime = info->time;
}



SNum mpcc_pacing_rate(struct mpcc *m, struct runtime_info *info) {
    //printf("%f\n", (double) m->rate/(double) m->cfg.bottleneckRate);
    return m->rate;
}


SNum mpcc_cwnd(struct mpcc *m, struct runtime_info *info) {
    SNum bdp = m->rate*m->cfg.targetRTT/(info->mss*US_PER_SEC);
    return mpcc_max(1, 2*bdp);
}


void mpcc_on_ack(struct mpcc *m, struct runtime_info *info) {
    SNum deliv, est, err, tau, num, den;

    m->minRate = mpcc_wma(m->minRate, (info->mss*US_PER_SEC)/info->lastRTT);
    m->minRate = mpcc_max(minDelta, m->minRate);
    //printf("%ld, %f\n", m->minRate, (double) m->minRate/(double) m->cfg.bottleneckRate);

    if (info->inflight < 8)
        m->mrtt = info->lastRTT;
    else
        m->mrtt = mpcc_wma(m->mrtt, info->lastRTT);

    m->devRTT = mpcc_wma(m->devRTT, mpcc_abs(info->lastRTT - m->mrtt));


    if (info->time > m->muTime + m->cfg.targetRTT) {
        deliv = (info->delivered - m->muDeliv)*info->mss;
        est = deliv/(info->time - m->muTime);

        if (m->mrtt > m->cfg.targetRTT)
            m->mu = est;
        else
            m->mu = mpcc_max(m->mu, est);

        m->mu = mpcc_clamp(m->mu, m->minRate, 2*m->cfg.bottleneckRate);

        m->muDeliv = info->delivered;
        m->muTime = info->time;
    }


    m->lastTime = info->time;

    err = m->cfg.targetRTT - m->mrtt;
    tau = 4*m->cfg.targetRTT;

    num = tau + err;
    den = tau;
    m->rate = (num*m->mu)/den;// + m->minRate;
    m->rate = mpcc_clamp(m->rate, m->minRate, 2*m->cfg.bottleneckRate);
}


void mpcc_on_loss(struct mpcc *m, struct runtime_info *info) {
}
