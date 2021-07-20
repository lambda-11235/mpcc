
#include "mpcc.h"


void updateMU(struct mpcc *m, struct runtime_info *info);


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

    m->predRTT = m->mrtt;
    m->err = 0;
    m->rate = m->minRate;

    m->ssthresh = m->cfg.bottleneckRate;
    m->recovery = false;

    m->mu = m->cfg.bottleneckRate;
    m->muACKed = 0;
    m->muTime = info->time;
}



SNum mpcc_pacing_rate(struct mpcc *m, struct runtime_info *info) {
    //printf("%f\n", (double) m->rate/(double) m->cfg.bottleneckRate);
    return m->rate;
}


SNum mpcc_cwnd(struct mpcc *m, struct runtime_info *info) {
    return mpcc_max(minDelta, 2*m->rate*m->cfg.targetRTT/(info->mss*US_PER_SEC));
}


void mpcc_on_ack(struct mpcc *m, struct runtime_info *info) {
    SNum tau, ref, num, den;

    m->minRate = mpcc_wma(m->minRate, (info->mss*US_PER_SEC)/info->lastRTT);
    m->minRate = mpcc_max(minDelta, m->minRate);
    //printf("%ld, %f\n", m->minRate, (double) m->minRate/(double) m->cfg.bottleneckRate);

    if (info->inflight < 8)
        m->mrtt = info->lastRTT;
    else
        m->mrtt = mpcc_wma(m->mrtt, info->lastRTT);

    m->devRTT = mpcc_wma(m->devRTT, mpcc_abs(info->lastRTT - m->mrtt));


    if (m->mrtt > 2*m->cfg.targetRTT)
        mpcc_on_loss(m, info);
    else if (m->mrtt > m->cfg.targetRTT)
        m->ssthresh = m->mu/4;

    updateMU(m, info);

    tau = 4*m->cfg.targetRTT;
    if (info->time > m->lastTime + tau) {
        m->lastTime = info->time;

        if (m->mu < m->ssthresh && !m->recovery) {
            m->err = 0;
            ref = 2*m->cfg.targetRTT;
        } else {
            m->err = mpcc_wma(m->err, m->mrtt - m->predRTT);
            ref = mpcc_wma(m->mrtt, m->cfg.targetRTT);
        }

        m->predRTT = m->mrtt + tau*(m->rate - m->mu)/m->mu;
        m->err = 0;

        num = m->cfg.targetRTT - m->err + ref - m->mrtt;
        den = m->cfg.targetRTT;
        m->rate = (num*m->mu)/den;
    }


    m->rate = mpcc_clamp(m->rate, m->minRate, 2*m->cfg.bottleneckRate);
}


void mpcc_on_loss(struct mpcc *m, struct runtime_info *info) {
    m->rate = m->mu/2;
    m->ssthresh = mpcc_min(m->ssthresh, m->mu/4);
    m->recovery = true;
}


void updateMU(struct mpcc *m, struct runtime_info *info) {
    SNum est;
    
    m->muACKed += 1;
    if (info->time > m->muTime + m->cfg.targetRTT) {
        est = (m->muACKed*info->mss*US_PER_SEC)/(info->time - m->muTime);

        if (m->mrtt > m->cfg.targetRTT)
            m->mu = est;
        else
            m->mu = mpcc_max(m->mu, est);

        //m->mu += m->minRate;

        m->mu = mpcc_clamp(m->mu, m->minRate, 2*m->cfg.bottleneckRate);

        m->muACKed = 0;
        m->muTime = info->time;
    }
};
