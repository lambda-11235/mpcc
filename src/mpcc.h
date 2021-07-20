
#include <stdbool.h>
#include <stdint.h>


#ifndef MPCC_H
#define MPCC_H


// minDelta is minimum delta, the minimum difference between two unequal
// values.

typedef int64_t SNum;
static const SNum minDelta = 1;

//typedef double SNum;
//static const SNum minDelta = 1.0e-10;


static const SNum US_PER_SEC = 1000000;


struct mpcc_config {
    // Rates are in bytes/s, times are in us, and percentages are out of 100.
    SNum bottleneckRate;
    SNum targetRTT;
};


struct mpcc {
    // Rates are in bytes/s, times are in us, and percentages are out of 100.
    struct mpcc_config cfg;

    SNum minRate;

    SNum mrtt, devRTT, lastTime;

    SNum predRTT, err, rate;

    SNum ssthresh;
    bool recovery;

    SNum mu, muACKed, muTime;
};


struct runtime_info {
    SNum time;
    SNum lastRTT;
    SNum inflight;
    SNum mss;
};


void mpcc_init(struct mpcc *m, const struct mpcc_config *cfg, struct runtime_info *info);
void mpcc_release(struct mpcc *m);
void mpcc_reset(struct mpcc *m, struct runtime_info *info);

SNum mpcc_pacing_rate(struct mpcc *m, struct runtime_info *info);
SNum mpcc_cwnd(struct mpcc *m, struct runtime_info *info);

void mpcc_on_ack(struct mpcc *m, struct runtime_info *info);
void mpcc_on_loss(struct mpcc *m, struct runtime_info *info);

#endif /* end of include guard: MPCC_H */
