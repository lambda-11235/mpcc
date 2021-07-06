
#include <stdbool.h>
#include <stdint.h>


#ifndef PID_H
#define PID_H


// minDelta is minimum delta, the minimum difference between two unequal
// values.

typedef int64_t SNum;
static const SNum minDelta = 1;

//typedef double SNum;
//static const SNum minDelta = 1.0e-10;


static const SNum US_PER_SEC = 1000000;


struct pid_config {
    // Rates are in bytes/s, times are in us, and percentages are out of 100.
    SNum bottleneckRate;
    SNum targetRTT;
};


struct pid {
    // Rates are in bytes/s, times are in us, and percentages are out of 100.
    struct pid_config cfg;

    SNum minRate, minRTT;
    SNum mrtt, devRTT, lastTime;
    SNum integ, lastErr, rate;
    SNum mu, muACKed, muTime;
};


struct runtime_info {
    SNum time;
    SNum lastRTT;
    SNum inflight;
    SNum mss;
};


void pid_init(struct pid *self, const struct pid_config *cfg, struct runtime_info *info);
void pid_release(struct pid *self);
void pid_reset(struct pid *self, struct runtime_info *info);

SNum pid_pacing_rate(struct pid *self, struct runtime_info *info);
SNum pid_cwnd(struct pid *self, struct runtime_info *info);

void pid_on_ack(struct pid *self, struct runtime_info *info);
void pid_on_loss(struct pid *self, struct runtime_info *info);

#endif /* end of include guard: PID_H */
