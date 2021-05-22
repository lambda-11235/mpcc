
#include <linux/limits.h>
#include <linux/spinlock.h>

#include "dfs.h"


static DEFINE_SPINLOCK(dfs_lock);


static int debugfs_s64_set(void *data, u64 val)
{
	*(s64 *)data = val;
	return 0;
}
static int debugfs_s64_get(void *data, u64 *val)
{
	*val = *(s64 *)data;
	return 0;
}
DEFINE_DEBUGFS_ATTRIBUTE(fops_s64, debugfs_s64_get, debugfs_s64_set, "%lld\n");


void mpcc_dfs_init(struct mpcc_dfs *dfs)
{
	dfs->root = debugfs_create_dir(MPC_DFS_DIR, NULL);
	dfs->alive = 0;
	dfs->next_id = 0;

	if (dfs->root == NULL)
		printk(KERN_WARNING "MPC: Failed to create root debugfs directory.\n");
}

void mpcc_dfs_release(struct mpcc_dfs *dfs)
{
	debugfs_remove_recursive(dfs->root);
}

void mpcc_dfs_register(struct mpcc_dfs *dfs, struct mpcc_dfs_stats *dstats,
	unsigned int daddr, unsigned int dport, unsigned int lport,
	struct mpcc *m)
{
	// We need to create a unique name for each DFS since multiple instances may
	// be running.
	char uniq_name[32];
	unsigned long flags;

	dstats->dir = NULL;
	dstats->daddr = daddr;
	dstats->dport = dport;
	dstats->lport = lport;

	sprintf(uniq_name, "%llu", dfs->next_id);


	spin_lock_irqsave(&dfs_lock, flags);

	if (dfs->root != NULL)
		dstats->dir = debugfs_create_dir(uniq_name, dfs->root);

	if (dstats->dir == NULL) {
		printk(KERN_WARNING "MPC: Failed to create debugfs directory.\n");
	} else {
		dfs->alive++;

		debugfs_create_u32("daddr", 0444, dstats->dir, &dstats->daddr);
		debugfs_create_u32("dport", 0444, dstats->dir, &dstats->dport);
		debugfs_create_u32("lport", 0444, dstats->dir, &dstats->lport);

		debugfs_create_file("INT_BPS", 0444, dstats->dir,
			&INT_BPS, &fops_s64);
		debugfs_create_file("set_rate", 0444, dstats->dir,
			&m->set_rate, &fops_s64);
		debugfs_create_file("target_rtt", 0444, dstats->dir,
			&m->target_rtt, &fops_s64);

		debugfs_create_file("rb", 0444, dstats->dir,
			&m->rb, &fops_s64);
		debugfs_create_file("lp", 0444, dstats->dir,
			&m->rtt_min[0], &fops_s64);
		debugfs_create_file("lb", 0444, dstats->dir,
			&m->rtt_max[0], &fops_s64);

		debugfs_create_file("rtt_avg", 0444, dstats->dir,
			&m->__debug_rtt_avg, &fops_s64);

		dfs->next_id = (dfs->next_id + 1) % ULLONG_MAX;
	}

	spin_unlock_irqrestore(&dfs_lock, flags);
}

void mpcc_dfs_unregister(struct mpcc_dfs *dfs, struct mpcc_dfs_stats *dstats)
{
	unsigned long flags;

	debugfs_remove_recursive(dstats->dir);

	spin_lock_irqsave(&dfs_lock, flags);
	dfs->alive--;
	spin_unlock_irqrestore(&dfs_lock, flags);
}
