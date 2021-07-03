
#include "mpcc.h"


void updateMU(struct mpcc *m, struct runtime_info *info);
void resetMUEst(struct mpcc *m, struct runtime_info *info);


SNum abs_i64(SNum x) {
    if (x < 0)
        return -x;
    else
        return x;
}

SNum min(SNum x, SNum y) {
    if (x < y)
        return x;
    else
        return y;
}

SNum max(SNum x, SNum y) {
    if (x > y)
        return x;
    else
        return y;
}

SNum clamp(SNum x, SNum min, SNum max) {
    if (x < min)
        return min;
    else if (x > max)
        return max;
    else
        return x;
}

SNum wma(SNum avg, SNum x) {
    return (9*avg + x)/10;
}



void mpcc_init(struct mpcc *m, const struct mpcc_config *cfg, struct runtime_info *info) {
    m->cfg = *cfg;
    mpcc_reset(m, info);
}


void mpcc_release(struct mpcc *m) {
}


void mpcc_reset(struct mpcc *m, struct runtime_info *info) {
    SNum time = info->time*M/m->cfg.targetRTT;
    SNum lastRTT = info->lastRTT*M/m->cfg.bottleneckRate;

    m->minRate = max(D, (info->mss*M)/(info->lastRTT*m->cfg.bottleneckRate));

    m->mrtt = lastRTT;
    m->devRTT = 0;
    m->lastTime = time;

    m->predRTT = m->mrtt;
    m->err = 0;
    m->rate = m->minRate;

    m->ssthresh = M;
    m->recovery = false;

    m->mu = m->rate;
    m->muInteg = 0;
    m->muRTT = m->mrtt;
    m->muTime = 0;
    m->muLastTime = 0;
}



SNum mpcc_pacing_rate(struct mpcc *m, struct runtime_info *info) {
    //printf("%f\n", (double) m->rate/(double) M);
    return m->rate*m->cfg.bottleneckRate/M;
}


SNum mpcc_cwnd(struct mpcc *m, struct runtime_info *info) {
    //printf("%ld\n", m->_cwnd);
    SNum rate = m->rate*m->cfg.bottleneckRate/M;
    SNum rtt = m->mrtt*m->cfg.targetRTT/M;
    return max(D, 2*rate*rtt/info->mss);
}


void mpcc_on_ack(struct mpcc *m, struct runtime_info *info) {
    SNum ref, num, den;
    SNum time = info->time*M/m->cfg.targetRTT;
    SNum lastRTT = info->lastRTT*M/m->cfg.targetRTT;

    m->minRate = wma(m->minRate,
                     (info->mss*M)/(info->lastRTT*m->cfg.bottleneckRate));
    m->minRate = max(D, m->minRate);
    //printf("%ld, %f\n", m->minRate, (double) m->minRate/(double) M);

    if (info->inflight < 8)
        m->mrtt = lastRTT;
    else
        m->mrtt = wma(m->mrtt, lastRTT);

    m->devRTT = wma(m->devRTT, abs_i64(lastRTT - m->mrtt));


    if (m->mrtt > 2*M)
        mpcc_on_loss(m, info);
    else if (m->mrtt > M)
        m->ssthresh = min(m->ssthresh, m->mu/4);

    updateMU(m, info);

    if (time > m->lastTime + M) {
        m->lastTime = time;
        m->ssthresh += m->minRate;

        if (m->mu < m->ssthresh && !m->recovery) {
            m->err = 0;
            ref = 2*M;
        } else {
            m->err = wma(m->err, m->mrtt - m->predRTT);
            ref = wma(m->mrtt, M);
        }

        num = M - m->err + ref - m->mrtt;
        den = M;
        m->rate = (num*m->mu)/den;

        m->predRTT = m->mrtt + M*(m->rate - m->mu)/m->mu;
    }


    m->rate = clamp(m->rate, m->minRate, 2*M);
}


void mpcc_on_loss(struct mpcc *m, struct runtime_info *info) {
    m->rate = m->mu/2;
    m->ssthresh = min(m->ssthresh, m->mu/4);
    m->recovery = true;
}


void updateMU(struct mpcc *m, struct runtime_info *info) {
    SNum dt, est;

    SNum time = info->time*M/m->cfg.targetRTT;
    SNum lastRTT = info->lastRTT*M/m->cfg.targetRTT;

    bool cond1 = m->muTime > 4*(M + m->devRTT);
    bool cond2 = m->muTime > M && m->mrtt > 2*M;


    if (cond1 || cond2) {
        est = m->muInteg/(m->muTime + m->mrtt - m->muRTT);

        if (est > m->mu)
            est += m->minRate;

        m->mu = est;

        resetMUEst(m, info);
        m->mu = clamp(m->mu, m->minRate, 2*M);
    } else {
        dt = time - m->muLastTime;
        m->muLastTime = time;

        m->muInteg += m->rate*dt;
        m->muTime += dt;
    }
};


void resetMUEst(struct mpcc *m, struct runtime_info *info) {;
    SNum time = info->time*M/m->cfg.targetRTT;
    SNum lastRTT = info->lastRTT*M/m->cfg.targetRTT;

    m->muInteg = 0;
    m->muRTT = m->mrtt;
    m->muTime = 0;
    m->muLastTime = time;
}
