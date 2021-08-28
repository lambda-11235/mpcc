
#include <linux/module.h>

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
    SNum baseRTT;
};


struct pid_control {
    // Rates are in bytes/s, times are in us, and percentages are out of 100.
    struct pid_config cfg;

    SNum minRate, minRTT;
    SNum targetRTT;
    SNum mrtt, devRTT;
    SNum rateLastTime, rttLastTime;
    SNum integ, rate, ssthresh;
    SNum mu, muDeliv, muTime;
};


struct runtime_info {
    SNum time;
    SNum lastRTT;
    SNum delivered;
    SNum inflight;
    SNum mss;
    SNum hops;
};


void pid_init(struct pid_control *self, const struct pid_config *cfg, struct runtime_info *info);
void pid_release(struct pid_control *self);
void pid_reset(struct pid_control *self, struct runtime_info *info);

SNum pid_pacing_rate(struct pid_control *self, struct runtime_info *info);
SNum pid_cwnd(struct pid_control *self, struct runtime_info *info);

void pid_on_ack(struct pid_control *self, struct runtime_info *info);
void pid_on_loss(struct pid_control *self, struct runtime_info *info);

#endif /* end of include guard: PID_H */
