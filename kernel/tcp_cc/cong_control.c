/*
 * net/sched/tcp_cc.c	A congestion control algorithm based on model predictive
 * control.
 *
 *		This program is free software; you can redistribute it and/or
 *		modify it under the terms of the GNU General Public License
 *		as published by the Free Software Foundation; either version
 *		2 of the License, or (at your option) any later version.
 *
 * Authors:	Taran Lynn <taranlynn0@gmail.com>
 */

#include <linux/module.h>
#include <net/tcp.h>

#include "../../src/pid.h"


#define PRINT_DELAY (NSEC_PER_SEC/10)


struct pid_config pid_default_config = {
    .bottleneckRate = ((SNum) 1) << 27,
    .baseRTT = 200,
    .flowGainNum = 200, .flowGainDen = 1000,
    .hopGainDen = 0, .hopGainDen = 1,
    .maxCWND = MAX_TCP_WINDOW,
    .maxFlows = 256
};

struct control {
    struct pid_control model;
    struct runtime_info info;
    u64 last_set_print_time;
    u64 last_report_print_time;
};


inline struct control* get_control(struct sock *sk) {
	struct control **ctlptr = inet_csk_ca(sk);
	return *ctlptr;
}

// Set the pacing rate. rate is in bytes/sec.
inline void set_rate(struct sock *sk) {
	struct control *ctl = get_control(sk);
	struct tcp_sock *tp = tcp_sk(sk);
        u64 now = ktime_get_ns();
	u32 max_cwnd = min_t(u32, MAX_TCP_WINDOW, tp->snd_cwnd_clamp);
        u64 rate, cwnd;

        ctl->info.time = now/NSEC_PER_USEC;

	rate = pid_pacing_rate(&ctl->model, &ctl->info);
	cwnd = pid_cwnd(&ctl->model, &ctl->info);

	sk->sk_pacing_rate = min_t(u64, max_t(u64, 1, rate), sk->sk_max_pacing_rate);
        tp->snd_cwnd = min_t(u64, max_t(u64, 1, cwnd), max_cwnd);

        if (now > ctl->last_set_print_time + PRINT_DELAY) {
            ctl->last_set_print_time = now;
            printk("pid_cc: Setting sk_pacing_rate = %lu, snd_cwnd = %u\n", sk->sk_pacing_rate, tp->snd_cwnd);
        }
}


void pid_cc_init(struct sock *sk)
{
	struct control **ctlptr = inet_csk_ca(sk);
	struct tcp_sock *tp = tcp_sk(sk);
	struct control *ctl = kzalloc(sizeof(struct control), GFP_KERNEL);
        u64 now = ktime_get_ns();

	if (ctl == NULL) {
		*ctlptr = NULL;
		return;
	}

	*ctlptr = ctl;

	tp->snd_ssthresh = TCP_INFINITE_SSTHRESH;
	sk->sk_pacing_status = SK_PACING_NEEDED;

        ctl->last_set_print_time = now;
        ctl->last_report_print_time = now;

        ctl->info.time = now/NSEC_PER_USEC;
        ctl->info.lastRTT = pid_default_config.baseRTT;
        ctl->info.delivered = 0;
        ctl->info.inflight = 0;
        ctl->info.mss = tp->mss_cache;
        ctl->info.hops = 1;

	pid_init(&ctl->model, &pid_default_config, &ctl->info);
}


void pid_cc_release(struct sock *sk)
{
	struct control **ctlptr = inet_csk_ca(sk);
	struct control *ctl = *ctlptr;

	if (ctl != NULL) {
		pid_release(&ctl->model);
	}

        kvfree(ctl);

	*ctlptr = NULL;
}


u32 pid_cc_ssthresh(struct sock *sk)
{
	struct tcp_sock *tp = tcp_sk(sk);

	return tp->snd_ssthresh;
}


u32 pid_cc_undo_cwnd(struct sock *sk)
{
	struct control *ctl = get_control(sk);
	struct tcp_sock *tp = tcp_sk(sk);

        ctl->info.time = ktime_get_ns()/NSEC_PER_USEC;
	pid_on_loss(&ctl->model, &ctl->info);
	set_rate(sk);

	return tp->snd_cwnd;
}


void pid_cc_pkts_acked(struct sock *sk, const struct ack_sample *sample)
{
	// sample->rtt_us = RTT of acknowledged packet.
}


void pid_cc_main(struct sock *sk, const struct rate_sample *rs)
{
	struct control *ctl = get_control(sk);
	struct tcp_sock *tp = tcp_sk(sk);
        u64 now;

	if (ctl != NULL && rs->rtt_us > 0) {
            now = ktime_get_ns();

            ctl->info.time = now/NSEC_PER_USEC;
            ctl->info.lastRTT = tp->rack.rtt_us;
            ctl->info.delivered = tp->delivered;
            ctl->info.inflight = tp->packets_out;
            ctl->info.mss = tp->mss_cache;
            ctl->info.hops = 1;

            pid_on_ack(&ctl->model, &ctl->info);
            set_rate(sk);

            if (now > ctl->last_report_print_time + PRINT_DELAY) {
                ctl->last_report_print_time = now;
                printk(KERN_INFO "pid_cc: time = %lld ms, rate = %lld, integ = %lld, target_rtt = %lld, srtt = %lld, base_rtt = %lld\n",
                       now/NSEC_PER_MSEC, ctl->model.rate, ctl->model.integ, ctl->model.targetRTT, ctl->model.srtt, ctl->model.cfg.baseRTT);
            }
        }
}


static struct tcp_congestion_ops tcp_pid_cc_cong_ops __read_mostly = {
	.flags          = TCP_CONG_NON_RESTRICTED,
	.name           = "pid_cc",
	.owner          = THIS_MODULE,

	.init           = pid_cc_init,
	.release        = pid_cc_release,
	.ssthresh       = pid_cc_ssthresh,
	.undo_cwnd      = pid_cc_undo_cwnd,
	.pkts_acked     = pid_cc_pkts_acked,
	.cong_control   = pid_cc_main,
};

static int __init pid_cc_mod_init(void)
{
	printk(KERN_INFO "mpc: module init\n");

	tcp_register_congestion_control(&tcp_pid_cc_cong_ops);

	printk(KERN_INFO "Flow: %lu bytes, model: %lu bytes\n",
		sizeof(struct control), sizeof(struct pid));

	return 0;
}

static void __exit pid_cc_mod_exit(void)
{
	printk(KERN_INFO "mpc: module exit\n");
	tcp_unregister_congestion_control(&tcp_pid_cc_cong_ops);
}

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Taran Lynn");
MODULE_DESCRIPTION("Model Predictive Congestion Control");
MODULE_VERSION("0.01");

module_init(pid_cc_mod_init);
module_exit(pid_cc_mod_exit);
