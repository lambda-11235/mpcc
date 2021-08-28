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


struct pid_config pid_default_config = {
    .bottleneckRate = 10 << 27,
    .targetRTT = 30000
};

struct control {
	struct pid_control model;
    SNum total_delivered;
};


inline struct control* get_control(struct sock *sk) {
	struct control **ctlptr = inet_csk_ca(sk);
	return *ctlptr;
}

inline void set_runtime_info(struct sock *sk, struct runtime_info* info) {
    struct tcp_sock *tp = tcp_sk(sk);

    info->time = ktime_get_ns()/NSEC_PER_SEC;
    info->lastRTT = tp->rack.rtt_us;
    info->delivered = tp->delivered;
    info->inflight = tp->packets_out;
    info->mss = tp->mss_cache;
}

// Set the pacing rate. rate is in bytes/sec.
inline void set_rate(struct sock *sk) {
	struct control *ctl = get_control(sk);
	struct tcp_sock *tp = tcp_sk(sk);
        struct runtime_info info;
	u32 max_cwnd = min_t(u32, MAX_TCP_WINDOW, tp->snd_cwnd_clamp);
        set_runtime_info(sk, &info);

	sk->sk_pacing_rate = pid_pacing_rate(&ctl->model, &info);

	//tp->snd_cwnd = max_cwnd;
	tp->snd_cwnd = pid_cwnd(&ctl->model, tp->mss_cache)/tp->mss_cache;
	tp->snd_cwnd = min_t(u32, max_t(u32, 1, tp->snd_cwnd), max_cwnd);
}


void pid_cc_init(struct sock *sk)
{
	struct control **ctlptr = inet_csk_ca(sk);
	struct tcp_sock *tp = tcp_sk(sk);
	struct control *ctl = kzalloc(sizeof(struct control), GFP_KERNEL);
        struct runtime_info info;
        set_runtime_info(sk, &info);

	if (ctl == NULL) {
		*ctlptr = NULL;
		return;
	}

	*ctlptr = ctl;

	tp->snd_ssthresh = TCP_INFINITE_SSTHRESH;
	sk->sk_pacing_status = SK_PACING_NEEDED;

	pid_init(&ctl->model, &pid_default_config, &info);
}


void pid_cc_release(struct sock *sk)
{
	struct control **ctlptr = inet_csk_ca(sk);
	struct control *ctl = *ctlptr;

	if (ctl != NULL) {
		pid_release(&ctl->model);
	}

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
        struct runtime_info info;
        set_runtime_info(sk, &info);

	pid_on_loss(&ctl->model, &info);
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
        struct runtime_info info;
        set_runtime_info(sk, &info);

	if (ctl != NULL && rs->rtt_us > 0) {
            pid_on_ack(&ctl->model, &info);
		set_rate(sk);
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
