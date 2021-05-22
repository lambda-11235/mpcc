
#include <linux/kobject.h>
#include <linux/sysctl.h>
#include <net/tcp.h>

#include "../../src/mpcc.h"

#ifndef SYSFS_H
#define SYSFS_H

struct mpcc_settings {
	bool has_kobj;
	struct kobject kobj;

	unsigned int daddr;
	unsigned int dport;
	unsigned int lport;
	struct mpcc_config *cfg;
};
#define to_mpcc_settings(x) container_of(x, struct mpcc_settings, kobj)


struct mpcc_attribute {
	struct attribute attr;
	ssize_t (*show)(struct mpcc_settings *settings, struct mpcc_attribute *attr, char *buf);
	ssize_t (*store)(struct mpcc_settings *settings, struct mpcc_attribute *attr, const char *buf, size_t count);
};
#define to_mpcc_attr(x) container_of(x, struct mpcc_attribute, attr)


int mpcc_sysfs_register(struct mpcc_settings *settings, struct kset *set,
	unsigned int daddr, unsigned int dport, unsigned int lport,
	struct mpcc *m);

int mpcc_sysfs_unregister(struct mpcc_settings *settings);

#endif /* end of include guard: SYSFS_H */
