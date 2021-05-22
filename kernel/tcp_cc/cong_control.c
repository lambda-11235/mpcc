/*
 * net/sched/mpcc_cc.c	A congestion control algorithm based on model predictive
 * control.
 *
 *		This program is free software; you can redistribute it and/or
 *		modify it under the terms of the GNU General Public License
 *		as published by the Free Software Foundation; either version
 *		2 of the License, or (at your option) any later version.
 *
 * Authors:	Taran Lynn <taranlynn0@gmail.com>
 */

#include <linux/kobject.h>
#include <linux/module.h>
#include <linux/sysctl.h>
#include <net/tcp.h>

#include "../../src/mpcc.h"
#include "../mpc/dfs.h"
#include "../mpc/sysfs.h"

static struct kset *mpcc_kset;
static struct mpcc_dfs debugfs;

struct control {
	struct mpcc m;
	struct mpcc_dfs_stats dfs;
	struct mpcc_settings settings;
};


inline struct control* get_control(struct sock *sk) {
	struct control **ctlptr = inet_csk_ca(sk);
	return *ctlptr;
}

// Set the pacing rate. rate is in bytes/sec.
inline void set_rate(struct sock *sk) {
	struct control *ctl = get_control(sk);
	struct tcp_sock *tp = tcp_sk(sk);
	u32 max_cwnd = min_t(u32, MAX_TCP_WINDOW, tp->snd_cwnd_clamp);

	sk->sk_pacing_rate = mpcc_pacing_rate(&ctl->m);

	//tp->snd_cwnd = max_cwnd;
	tp->snd_cwnd = mpcc_cwnd(&ctl->m, tp->mss_cache)/tp->mss_cache;
	tp->snd_cwnd = min_t(u32, max_t(u32, 1, tp->snd_cwnd), max_cwnd);
}


void mpcc_cc_init(struct sock *sk)
{
	struct control **ctlptr = inet_csk_ca(sk);
	struct tcp_sock *tp = tcp_sk(sk);
	struct control *ctl = kzalloc(sizeof(struct control), GFP_KERNEL);
	u32 addr = be32_to_cpu(sk->sk_daddr);
	u16 port = be16_to_cpu(sk->sk_dport);
	u64 now = ktime_get_ns();

	if (ctl == NULL) {
		*ctlptr = NULL;
		return;
	}

	*ctlptr = ctl;

	tp->snd_ssthresh = TCP_INFINITE_SSTHRESH;
	sk->sk_pacing_status = SK_PACING_NEEDED;


	mpcc_init(&ctl->m, &mpcc_default_config, now/NSEC_PER_USEC);
	mpcc_sysfs_register(&ctl->settings, mpcc_kset, addr, port, sk->sk_num,
		&ctl->m);
	mpcc_dfs_register(&debugfs, &ctl->dfs, addr, port, sk->sk_num, &ctl->m);
}


void mpcc_cc_release(struct sock *sk)
{
	struct control **ctlptr = inet_csk_ca(sk);
	struct control *ctl = *ctlptr;

	if (ctl != NULL) {
		mpcc_dfs_unregister(&debugfs, &ctl->dfs);
		mpcc_sysfs_unregister(&ctl->settings);
		mpcc_release(&ctl->m);
	}

	*ctlptr = NULL;
}


u32 mpcc_cc_ssthresh(struct sock *sk)
{
	struct tcp_sock *tp = tcp_sk(sk);

	return tp->snd_ssthresh;
}


u32 mpcc_cc_undo_cwnd(struct sock *sk)
{
	struct control *ctl = get_control(sk);
	struct tcp_sock *tp = tcp_sk(sk);
	u64 now = ktime_get_ns();

	mpcc_on_loss(&ctl->m, now/NSEC_PER_USEC);
	set_rate(sk);

	return tp->snd_cwnd;
}


void mpcc_cc_pkts_acked(struct sock *sk, const struct ack_sample *sample)
{
	// sample->rtt_us = RTT of acknowledged packet.
}


void mpcc_cc_main(struct sock *sk, const struct rate_sample *rs)
{
	struct control *ctl = get_control(sk);
	struct tcp_sock *tp = tcp_sk(sk);
	u64 now = ktime_get_ns();
	u64 rate_est = 0;

	if (rs->delivered > 0 && rs->interval_us > 0)
		rate_est = rs->delivered*tp->mss_cache*US_PER_SEC/rs->interval_us;

	// rs->rtt_us = RTT of last packet to be acknowledged.
	// tp->srtt_us = WMA of RTT
	// tp->tp->mdev_us = Variance of WMA of RTT

	if (ctl != NULL && rs->rtt_us > 0) {
		mpcc_on_ack(&ctl->m, now/NSEC_PER_USEC, rate_est, rs->rtt_us);
		set_rate(sk);
	}
}


static struct tcp_congestion_ops tcp_mpcc_cc_cong_ops __read_mostly = {
	.flags          = TCP_CONG_NON_RESTRICTED,
	.name           = "mpcc_cc",
	.owner          = THIS_MODULE,

	.init           = mpcc_cc_init,
	.release        = mpcc_cc_release,
	.ssthresh       = mpcc_cc_ssthresh,
	.undo_cwnd      = mpcc_cc_undo_cwnd,
	.pkts_acked     = mpcc_cc_pkts_acked,
	.cong_control   = mpcc_cc_main,
};

static int __init mpcc_cc_mod_init(void)
{
	printk(KERN_INFO "mpc: module init\n");

	mpcc_kset = kset_create_and_add("mpcc", NULL, kernel_kobj);
	if (!mpcc_kset)
		return -ENOMEM;

	mpcc_dfs_init(&debugfs);
	tcp_register_congestion_control(&tcp_mpcc_cc_cong_ops);

	printk(KERN_INFO "Flow: %lu bytes, model: %lu bytes\n",
		sizeof(struct control), sizeof(struct mpcc));

	return 0;
}

static void __exit mpcc_cc_mod_exit(void)
{
	printk(KERN_INFO "mpc: module exit\n");
	tcp_unregister_congestion_control(&tcp_mpcc_cc_cong_ops);
	mpcc_dfs_release(&debugfs);
	kset_unregister(mpcc_kset);
}

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Taran Lynn");
MODULE_DESCRIPTION("Model Predictive Congestion Control");
MODULE_VERSION("0.01");

module_init(mpcc_cc_mod_init);
module_exit(mpcc_cc_mod_exit);
