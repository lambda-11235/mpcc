
#include <linux/debugfs.h>

#include "../../src/mpcc.h"

#ifndef DFS_H
#define DFS_H

#define MPC_DFS_DIR "mpcc"

struct mpcc_dfs {
	struct dentry *root;
	unsigned long long alive;
	unsigned long long next_id;
};

struct mpcc_dfs_stats {
	struct dentry *dir;

	unsigned int daddr;
	unsigned int dport;
	unsigned int lport;
};


void mpcc_dfs_init(struct mpcc_dfs *dfs);
void mpcc_dfs_release(struct mpcc_dfs *dfs);

void mpcc_dfs_register(struct mpcc_dfs *dfs, struct mpcc_dfs_stats *dstats,
	unsigned int daddr, unsigned int dport, unsigned int lport,
	struct mpcc *m);
void mpcc_dfs_unregister(struct mpcc_dfs *dfs, struct mpcc_dfs_stats *dstats);

#endif /* end of include guard: DFS_H */
