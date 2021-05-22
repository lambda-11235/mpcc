/*
 * A congestion control algorithm that forces cycling through a range. Used for
 * testing purposes.
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


#define MIN_CWND (1)
#define MAX_CWND (1<<30)
#define INC_CWND (1<<10)
#define SECS 1

struct control {
	long cwnd;
	long next_time;
};


inline struct control* get_control(struct sock *sk) {
	struct control **ctlptr = inet_csk_ca(sk);
	return *ctlptr;
}


void cwnd_tester_init(struct sock *sk)
{
	struct control **ctlptr = inet_csk_ca(sk);
	struct tcp_sock *tp = tcp_sk(sk);
	struct control *ctl = kzalloc(sizeof(struct control), GFP_KERNEL);

	if (ctl == NULL) {
		*ctlptr = NULL;
		return;
	}

	*ctlptr = ctl;
	ctl->cwnd = MIN_CWND;
	ctl->next_time = ktime_get_ns() + SECS*NSEC_PER_SEC;

	tp->snd_ssthresh = TCP_INFINITE_SSTHRESH;
}


void cwnd_tester_release(struct sock *sk)
{
	struct control **ctlptr = inet_csk_ca(sk);
	*ctlptr = NULL;
}


u32 cwnd_tester_ssthresh(struct sock *sk)
{
	struct tcp_sock *tp = tcp_sk(sk);

	return tp->snd_ssthresh;
}


void cwnd_tester_avoid(struct sock *sk, u32 ack, u32 acked)
{
}


u32 cwnd_tester_undo_cwnd(struct sock *sk)
{
	struct tcp_sock *tp = tcp_sk(sk);
	return tp->snd_cwnd;
}


void cwnd_tester_pkts_acked(struct sock *sk, const struct ack_sample *sample)
{
}


void cwnd_tester_main(struct sock *sk, const struct rate_sample *rs)
{
	struct control *ctl = get_control(sk);
	struct tcp_sock *tp = tcp_sk(sk);
	long now = ktime_get_ns();

	if (ctl != NULL) {
		if (ctl->next_time <= now) {
			ctl->next_time = now + SECS*NSEC_PER_SEC;

			//ctl->cwnd += INC_CWND;
			ctl->cwnd *= 2;

			if (ctl->cwnd > MAX_CWND)
				ctl->cwnd = MIN_CWND;

			tp->snd_cwnd = ctl->cwnd;
		}
	}
}


static struct tcp_congestion_ops tcp_cwnd_tester_cong_ops __read_mostly = {
	.flags          = TCP_CONG_NON_RESTRICTED,
	.name           = "cwnd_tester",
	.owner          = THIS_MODULE,

	.init           = cwnd_tester_init,
	.release        = cwnd_tester_release,
	.ssthresh       = cwnd_tester_ssthresh,
	.cong_avoid     = cwnd_tester_avoid,
	.undo_cwnd      = cwnd_tester_undo_cwnd,
	.pkts_acked     = cwnd_tester_pkts_acked,
	.cong_control   = cwnd_tester_main,
};

static int __init cwnd_tester_mod_init(void)
{
	tcp_register_congestion_control(&tcp_cwnd_tester_cong_ops);

	return 0;
}

static void __exit cwnd_tester_mod_exit(void)
{
	tcp_unregister_congestion_control(&tcp_cwnd_tester_cong_ops);
}

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Taran Lynn");
MODULE_DESCRIPTION("Model Predictive Congestion Control");
MODULE_VERSION("0.01");

module_init(cwnd_tester_mod_init);
module_exit(cwnd_tester_mod_exit);
