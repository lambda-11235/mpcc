/*
 * net/sched/sch_mpc.c	A model predictive control QDisc.
 *
 *		This program is free software; you can redistribute it and/or
 *		modify it under the terms of the GNU General Public License
 *		as published by the Free Software Foundation; either version
 *		2 of the License, or (at your option) any later version.
 *
 * Authors:	Taran Lynn <taranlynn0@gmail.com>
 */

#include <linux/module.h>
#include <linux/slab.h>
#include <linux/types.h>
#include <linux/kernel.h>
#include <linux/errno.h>
#include <linux/skbuff.h>
#include <net/pkt_sched.h>
#include <net/tcp.h>
#include <linux/version.h>

#include "../mpc/control.h"
#include "../mpc/sysfs.h"
#include "sch_mpc.h"


#define MAX_FLOWS (1 << 10)
#define HT_BITS (5)
#define RESET_DELAY (100*NSEC_PER_USEC) // In ns

static struct kset *mpc_kset;


struct mpc_flow {
	u32 addr;

	// Empty indicates not in q->sending.
	struct list_head send_list;
	struct hlist_node hash_list;

	struct sk_buff *head;
	struct sk_buff *tail;
	size_t qlen;

	struct model md;
	struct mpc_settings settings;

	// The pacing rate to send in bytes per second, set by model and
	// measured, respectively.
	u64 set_rate;
	u64 meas_rate;
	u64 last_bytes_sent;
	u64 bytes_sent;
	u64 time_last_sent;
	u64 time_start;

	// The time at which the next packet should be sent.
	u64 time_to_send;

	// Last smoothed rtt seen by the model.
	u32 last_srtt;
};


struct mpc_sched_data {
	// The flows. This is a hash map from destination addresses to flows.
	DECLARE_HASHTABLE(flows, HT_BITS);
	size_t num_flows;

	// Flow to use when classification fails or we are at our limit.
	struct mpc_flow def_flow;

	// Watchdog to set a timeout.
	struct qdisc_watchdog watchdog;

	// A list of flows that need to send packets, ordered by sending time
	// (smallest to largest).
	struct list_head sending;
};


static struct mpc_dfs debugfs;


static int flow_init(struct mpc_flow *flow, u64 addr)
{
	flow->addr = addr;
	INIT_LIST_HEAD(&flow->send_list);
	INIT_HLIST_NODE(&flow->hash_list);

	flow->head = NULL;
	flow->tail = NULL;
	flow->qlen = 0;

	flow->set_rate = 0;
	flow->meas_rate = 0;
	flow->last_bytes_sent = 0;
	flow->bytes_sent = 0;
	flow->time_last_sent = 0;
	flow->time_start = ktime_get_ns();

	flow->time_to_send = 0;

	flow->last_srtt = 0;


	// NOTE: We just assign dport and lport to 0, since there could be
	// multiple ports associated with a flow.
	mpc_sysfs_register(&flow->settings, mpc_kset, addr, 0, 0,
		95*1024/100, 10*1024/100, 1, 8,
		1 << 10, 25 << 10,
		1*1024/100, 1*1024/100);

	model_init(&flow->md, &flow->settings);

	mpc_dfs_register(&debugfs, &flow->md.stats, addr, 0, 0);

	return 0;
}

static void flow_release(struct mpc_flow *flow)
{
	mpc_dfs_unregister(&debugfs, &flow->md.stats);
	model_release(&flow->md);
	mpc_sysfs_unregister(&flow->settings);
}


static void flow_enqueue(struct mpc_flow *flow, struct sk_buff *skb)
{
	if (flow->head == NULL)
		flow->head = skb;
	else
		flow->tail->next = skb;

	flow->tail = skb;
	skb->next = NULL;

	flow->qlen++;
}

inline static struct sk_buff *flow_peek(struct mpc_flow *flow)
{
	return flow->head;
}

static struct sk_buff *flow_dequeue(struct mpc_flow *flow)
{
	struct sk_buff *skb = flow->head;

	if (skb != NULL) {
		flow->head = skb->next;
		skb->next = NULL;

		if (flow->head == NULL)
			flow->tail = NULL;

		flow->qlen--;
	}

	return skb;
}


static void flow_update_time_to_send(struct mpc_flow *flow, u64 now)
{
	u64 min_delay;

	if (flow->set_rate > 0) {
		min_delay = flow->bytes_sent + flow->last_bytes_sent;
		min_delay *= NSEC_PER_SEC;
		min_delay /= flow->set_rate;
		min_delay -= now - flow->time_start;
	} else {
		min_delay = 0;
	}

	// Take the max here to ensure that we don't go past the max rate on a
	// burst.
	flow->time_to_send = max_t(u64, now, flow->time_last_sent + min_delay);
}

static void flow_update_rate(struct mpc_flow *flow, u64 srtt_us, u64 now)
{
	// srtt' = (1 - a) * srtt + a * rtt
	// rtt = srtt + (srtt' - srtt)/a
	// Reading the sources tells us that a = 1/8.
	// We have to make sure we get a positive rtt, otherwise estimate as
	// srtt.
	//
	// TODO: Don't hardcode alpha.
	u64 rtt;
	u64 t1 = flow->last_srtt + 8*srtt_us;
	u64 t2 = 8*flow->last_srtt;

	if (t1 > t2)
		rtt = t1 - t2;
	else
		rtt = 0;

	model_change(&flow->md, &flow->settings);

	flow->set_rate = control_process(&flow->md,
		now/NSEC_PER_USEC, flow->meas_rate >> 20, rtt, 0) << 20;
}


// Returns the flow that skb is a part of. Creates a new flow if necessary.
static struct mpc_flow *mpc_classify(struct Qdisc *sch, struct sk_buff *skb)
{
	// NOTE: I'm classifying by destination address. fq classifies by
	// socket, and fq_codel uses a classiful qdisc (even though it isn't
	// classful, *it's wierd*).
	struct mpc_sched_data *q = qdisc_priv(sch);
	struct mpc_flow *flow = NULL;
	struct mpc_flow *it;
	u32 addr;

	if (skb->sk == NULL || q->num_flows >= MAX_FLOWS)
		goto class_default;

	addr = skb->sk->sk_daddr;
	addr = be32_to_cpu(addr);

	hash_for_each_possible(q->flows, it, hash_list, addr) {
		if (it->addr == addr)
			flow = it;
	}

	if (flow == NULL) {
		flow = kmalloc(sizeof(struct mpc_flow), GFP_KERNEL);

		if (flow == NULL) {
			goto class_default;
		} else if (flow_init(flow, addr)) {
			kfree(flow);
			goto class_default;
		}

		hash_add(q->flows, &flow->hash_list, flow->addr);

		q->num_flows++;
	}

	return flow;

class_default:
	return &q->def_flow;
}


// Add a flow to the list of flows that have a packet to send.
static void mpc_add_flow(struct Qdisc *sch, struct mpc_flow *flow)
{
	// We want to add the flow just in front of the last one sending sooner
	// than it.

	struct mpc_sched_data *q = qdisc_priv(sch);
	struct mpc_flow *it;
	struct list_head *last = &q->sending;

	if (list_empty(&flow->send_list)) {
		list_for_each_entry(it, &q->sending, send_list) {
			if (it->time_to_send <= flow->time_to_send)
				last = &it->send_list;
			else
				break;
		}

		list_add(&flow->send_list, last);
	}
}


// Remove a flow from the list of flows that have a packet to send.
static void mpc_del_flow(struct Qdisc *sch, struct mpc_flow *flow)
{
	list_del_init(&flow->send_list);
}


// Returns the next flow that needs to send a packet at time. If not such flow
// exists NULL is returned.
static struct mpc_flow *mpc_get_next_flow(struct Qdisc *sch)
{
	struct mpc_sched_data *q = qdisc_priv(sch);

	if (list_empty(&q->sending))
		return NULL;
	else
		return list_first_entry(&q->sending, struct mpc_flow, send_list);
}


// Update watchdog to dequeue when the next packet is ready.
static void mpc_update_watchdog(struct Qdisc *sch, u64 now)
{
	struct mpc_sched_data *q = qdisc_priv(sch);
	struct mpc_flow *flow = mpc_get_next_flow(sch);

	if (flow != NULL)
		qdisc_watchdog_schedule_ns(&q->watchdog, flow->time_to_send);
	else
		qdisc_watchdog_cancel(&q->watchdog);
}


static int mpc_enqueue(struct sk_buff *skb, struct Qdisc *sch,
		struct sk_buff **to_free)
{
	struct mpc_flow *flow = mpc_classify(sch, skb);
	u64 now = ktime_get_ns();

	// Reset flow if nothing has been sent on it in a while.
	if (flow->qlen == 0 && now - flow->time_last_sent > RESET_DELAY) {
		flow->bytes_sent = 0;
		flow->time_start = now;
	}

	if (flow == NULL || flow->qlen == sch->limit) {
		return qdisc_drop(skb, sch, to_free);
	} else if (skb != NULL) {
		flow_enqueue(flow, skb);
		flow_update_time_to_send(flow, now);
		mpc_add_flow(sch, flow);
		mpc_update_watchdog(sch, now);
	}

	return 0;
}


static struct sk_buff *mpc_dequeue(struct Qdisc *sch)
{
	struct mpc_flow *flow;
	struct sk_buff *skb = NULL;
	u64 now = ktime_get_ns();

	flow = mpc_get_next_flow(sch);

	if (flow == NULL || flow->time_to_send > now) {
		skb = NULL;
		goto exit_dequeue;
	}

	skb = flow_dequeue(flow);
	mpc_del_flow(sch, flow);

	flow->meas_rate = flow->meas_rate*7/8 +
		flow->last_bytes_sent*NSEC_PER_SEC/(now - flow->time_last_sent)/8;

	flow->bytes_sent += flow->last_bytes_sent;
	flow->last_bytes_sent = skb->len;
	flow->time_last_sent = now;

	if (flow->qlen > 0) {
		flow_update_time_to_send(flow, now);
		mpc_add_flow(sch, flow);
	}

	// Update rate using MPC.
	if (skb->sk != NULL && skb->sk->sk_protocol == IPPROTO_TCP) {
		struct tcp_sock *tp = tcp_sk(skb->sk);
		flow_update_rate(flow, tp->srtt_us, now);
	}

exit_dequeue:
	mpc_update_watchdog(sch, now);

	// Returns a packet to send out, NULL if we don't send out any.
	return skb;
}


static struct sk_buff *mpc_peek(struct Qdisc *sch) {
	struct mpc_flow *flow = mpc_get_next_flow(sch);

	if (flow != NULL)
		return flow_peek(flow);
	else
		return NULL;
}


static const struct nla_policy mpc_policy[TCA_MPC_MAX + 1] = {
	[TCA_MPC_LIMIT]			= { .type = NLA_U32 },
};

#if LINUX_VERSION_CODE <= KERNEL_VERSION(4,16,0)
static int mpc_change(struct Qdisc *sch, struct nlattr *opt)
#else
static int mpc_change(struct Qdisc *sch, struct nlattr *opt,
		struct netlink_ext_ack *extack)
#endif
{
	struct nlattr *tb[TCA_MPC_MAX + 1];
	int err;

	if (opt == NULL)
		return -EINVAL;

	err = nla_parse_nested(tb, TCA_MPC_MAX, opt, mpc_policy, NULL);
	if (err < 0)
		return err;

	if (tb[TCA_MPC_LIMIT])
		sch->limit = nla_get_u32(tb[TCA_MPC_LIMIT]);

	return err;
}

// FIXME: This is a quick fix to make it compile on 4.15 and 4.17.
#if LINUX_VERSION_CODE <= KERNEL_VERSION(4,16,0)
static int mpc_init(struct Qdisc *sch, struct nlattr *opt)
#else
static int mpc_init(struct Qdisc *sch, struct nlattr *opt,
		struct netlink_ext_ack *extack)
#endif
{
	struct mpc_sched_data *q = qdisc_priv(sch);

	hash_init(q->flows);
	q->num_flows = 0;
	flow_init(&q->def_flow, 0);
	qdisc_watchdog_init(&q->watchdog, sch);
	INIT_LIST_HEAD(&q->sending);

	sch->limit = qdisc_dev(sch)->tx_queue_len;

	if (opt) {
#if LINUX_VERSION_CODE <= KERNEL_VERSION(4,16,0)
		mpc_change(sch, opt);
#else
		mpc_change(sch, opt, extack);
#endif
	}

	return 0;
}

static int mpc_dump(struct Qdisc *sch, struct sk_buff *skb)
{
	struct nlattr *opts;

	opts = nla_nest_start(skb, TCA_OPTIONS);
	if (opts == NULL)
		goto nla_put_failure;

	if (nla_put_u32(skb, TCA_MPC_LIMIT, sch->limit))
		goto nla_put_failure;

	return nla_nest_end(skb, opts);

nla_put_failure:
	return -1;
}


static void mpc_destroy(struct Qdisc *sch);

static void mpc_reset(struct Qdisc *sch)
{
	struct mpc_sched_data *q = qdisc_priv(sch);

	mpc_destroy(sch);

	hash_init(q->flows);
	q->num_flows = 0;
	flow_init(&q->def_flow, 0);
	INIT_LIST_HEAD(&q->sending);

	qdisc_reset_queue(sch);
	qdisc_watchdog_cancel(&q->watchdog);
}

static void mpc_destroy(struct Qdisc *sch)
{
	struct mpc_sched_data *q = qdisc_priv(sch);
	struct hlist_node tmp;
	struct hlist_node *tmpp = &tmp;
	struct mpc_flow *it;
	size_t bkt;

	hash_for_each_safe(q->flows, bkt, tmpp, it, hash_list) {
		hash_del(&it->hash_list);
		flow_release(it);
		kfree(it);
	}

	flow_release(&q->def_flow);
}


struct Qdisc_ops mpc_qdisc_ops __read_mostly = {
	.id		=	"mpc",
	.priv_size	=	sizeof(struct mpc_sched_data),
	.enqueue	=	mpc_enqueue,
	.dequeue	=	mpc_dequeue,
	.peek		=	mpc_peek,
	.init		=	mpc_init,
	.reset		=	mpc_reset,
	.destroy        =       mpc_destroy,
	.change		=	mpc_change,
	.dump		=	mpc_dump,
	.owner		=	THIS_MODULE,
};
EXPORT_SYMBOL(mpc_qdisc_ops);


MODULE_LICENSE("GPL");
MODULE_AUTHOR("Taran Lynn");
MODULE_DESCRIPTION("A Qdisc that uses model predictive control.");
MODULE_VERSION("0.01");

static int __init mpcqd_init(void) {
	mpc_kset = kset_create_and_add("mpccc", NULL, kernel_kobj);
	if (!mpc_kset)
		return -ENOMEM;

	mpc_dfs_init(&debugfs);
	register_qdisc(&mpc_qdisc_ops);
	printk(KERN_INFO "Loaded module mpcqd\n");

	printk(KERN_INFO "Flow: %lu bytes, model: %lu bytes\n",
		sizeof(struct mpc_flow), sizeof(struct model));

	return 0;
}

static void __exit mpcqd_exit(void) {
	mpc_dfs_release(&debugfs);
	unregister_qdisc(&mpc_qdisc_ops);
	kset_unregister(mpc_kset);
	printk(KERN_INFO "Removed module mpcqd\n");
}

module_init(mpcqd_init);
module_exit(mpcqd_exit);
