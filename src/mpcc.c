
#include "mpcc.h"


void mpcc_init(struct mpcc *m, const struct mpcc_config *cfg, int64_t time){
}


void mpcc_release(struct mpcc *m){
}


void mpcc_reset(struct mpcc *m, int64_t time){
}



uint64_t mpcc_pacing_rate(struct mpcc *m, struct runtime_info *info){
    return 0;
}


uint64_t mpcc_cwnd(struct mpcc *m, struct runtime_info *info){
    return 0;
}



void mpcc_on_ack(struct mpcc *m, struct runtime_info *info){
}


void mpcc_on_loss(struct mpcc *m, struct runtime_info *info){
}


