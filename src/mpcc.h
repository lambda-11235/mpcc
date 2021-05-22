
#include <stdint.h>

#ifndef MPCC_H
#define MPCC_H


// How many bytes per second data is internally stored as.
// FIXME: This is problematic with many flows
static const int64_t INT_BPS = 1 << (16 - 3); // 64kbps


struct mpcc_config {
    // Rates are in bytes/s, times are in us, and percentages are out of 100.
    int64_t min_rate, max_rate;
    int64_t weight_rate, weight_rtt, weight_rtt_var;
    int64_t desired_rtt;
};

static const struct mpcc_config mpcc_default_config = {
    .min_rate = 100 << 17,
    .max_rate = 80UL << 27,
    .weight_rate = 1,
    .weight_rtt = 1,
    .weight_rtt_var = 1,
    .desired_rtt = 0,
};


struct mpcc {
    // Rates are in bytes/s, times are in us, and percentages are out of 100.
    struct mpcc_config cfg;
};


struct runtime_info {
    int64_t time;
    int64_t rtt;
    int64_t inflight;
    int64_t mss;
};


void mpcc_init(struct mpcc *m, const struct mpcc_config *cfg, int64_t time);
void mpcc_release(struct mpcc *m);
void mpcc_reset(struct mpcc *m, int64_t time);

uint64_t mpcc_pacing_rate(struct mpcc *m, struct runtime_info *info);
uint64_t mpcc_cwnd(struct mpcc *m, struct runtime_info *info);

void mpcc_on_ack(struct mpcc *m, struct runtime_info *info);
void mpcc_on_loss(struct mpcc *m, struct runtime_info *info);

#endif /* end of include guard: MPCC_H */
