
#include "sysfs.h"


static unsigned long id_count = 0;


static ssize_t settings_attr_show(struct kobject *kobj,
	struct attribute *attr, char *buf)
{
	struct mpcc_attribute *attribute;
	struct mpcc_settings *settings;

	attribute = to_mpcc_attr(attr);
	settings = to_mpcc_settings(kobj);

	if (!attribute->show)
		return -EIO;

	return attribute->show(settings, attribute, buf);
}


static ssize_t settings_attr_store(struct kobject *kobj,
	struct attribute *attr, const char *buf, size_t len)
{
	struct mpcc_attribute *attribute;
	struct mpcc_settings *settings;

	attribute = to_mpcc_attr(attr);
	settings = to_mpcc_settings(kobj);

	if (!attribute->store)
		return -EIO;

	return attribute->store(settings, attribute, buf, len);
}


static const struct sysfs_ops sysfs_ops = {
	.show = settings_attr_show,
	.store = settings_attr_store,
};


static void release(struct kobject *kobj)
{
	//struct mpcc_settings *settings = to_mpcc_settings(kobj);
}


static ssize_t mpcc_attr_show(struct mpcc_settings *settings, struct mpcc_attribute *attr,
	char *buf)
{
	unsigned long var;

	if (strcmp(attr->attr.name, "daddr") == 0)
		var = settings->daddr;
	if (strcmp(attr->attr.name, "dport") == 0)
		var = settings->dport;
	if (strcmp(attr->attr.name, "lport") == 0)
		var = settings->lport;

	if (strcmp(attr->attr.name, "min_rate") == 0)
		var = settings->cfg->min_rate;
	if (strcmp(attr->attr.name, "max_rate") == 0)
		var = settings->cfg->max_rate;
	if (strcmp(attr->attr.name, "weight_rate") == 0)
		var = settings->cfg->weight_rate;
	if (strcmp(attr->attr.name, "weight_rtt") == 0)
		var = settings->cfg->weight_rtt;
	if (strcmp(attr->attr.name, "desired_rate") == 0)
		var = settings->cfg->desired_rate;
	if (strcmp(attr->attr.name, "cycle_rtts") == 0)
		var = settings->cfg->cycle_rtts;
	if (strcmp(attr->attr.name, "rb_per_cycle") == 0)
		var = settings->cfg->rb_per_cycle;
	if (strcmp(attr->attr.name, "max_rtt_gain") == 0)
		var = settings->cfg->max_rtt_gain;

	return sprintf(buf, "%lu\n", var);
}


static ssize_t mpcc_attr_store(struct mpcc_settings *settings, struct mpcc_attribute *attr,
	const char *buf, size_t count)
{
	unsigned long var, ret;

	ret = kstrtoul(buf, 10, &var);
	if (ret < 0)
		return ret;

	// NOTE: Don't do the following, it should never be set.
	//if (strcmp(attr->attr.name, "port") == 0)
	//	settings->port = var;

	if (strcmp(attr->attr.name, "min_rate") == 0)
		settings->cfg->min_rate = var;
	if (strcmp(attr->attr.name, "max_rate") == 0)
		settings->cfg->max_rate = var;
	if (strcmp(attr->attr.name, "weight_rate") == 0)
		settings->cfg->weight_rate = var;
	if (strcmp(attr->attr.name, "weight_rtt") == 0)
		settings->cfg->weight_rtt = var;
	if (strcmp(attr->attr.name, "desired_rate") == 0)
		settings->cfg->desired_rate = var;
	if (strcmp(attr->attr.name, "cycle_rtts") == 0)
		settings->cfg->cycle_rtts = var;
	if (strcmp(attr->attr.name, "rb_per_cycle") == 0)
		settings->cfg->rb_per_cycle = var;
	if (strcmp(attr->attr.name, "max_rtt_gain") == 0)
		settings->cfg->max_rtt_gain = var;

	return count;
}

static struct mpcc_attribute daddr_attribute =
	__ATTR(daddr, 0444, mpcc_attr_show, mpcc_attr_store);
static struct mpcc_attribute dport_attribute =
	__ATTR(dport, 0444, mpcc_attr_show, mpcc_attr_store);
static struct mpcc_attribute lport_attribute =
	__ATTR(lport, 0444, mpcc_attr_show, mpcc_attr_store);

static struct mpcc_attribute min_rate_attribute =
	__ATTR(min_rate, 0644, mpcc_attr_show, mpcc_attr_store);
static struct mpcc_attribute max_rate_attribute =
	__ATTR(max_rate, 0644, mpcc_attr_show, mpcc_attr_store);
static struct mpcc_attribute weight_rate_attribute =
	__ATTR(weight_rate, 0644, mpcc_attr_show, mpcc_attr_store);
static struct mpcc_attribute weight_rtt_attribute =
	__ATTR(weight_rtt, 0644, mpcc_attr_show, mpcc_attr_store);
static struct mpcc_attribute desired_rate_attribute =
	__ATTR(desired_rate, 0644, mpcc_attr_show, mpcc_attr_store);
static struct mpcc_attribute cycle_rtts_attribute =
	__ATTR(cycle_rtts, 0644, mpcc_attr_show, mpcc_attr_store);
static struct mpcc_attribute rb_per_cycle_attribute =
	__ATTR(rb_per_cycle, 0644, mpcc_attr_show, mpcc_attr_store);
static struct mpcc_attribute max_rtt_gain_attribute =
	__ATTR(max_rtt_gain, 0644, mpcc_attr_show, mpcc_attr_store);


static struct attribute *default_attrs[] = {
	&daddr_attribute.attr,
	&dport_attribute.attr,
	&lport_attribute.attr,

	&min_rate_attribute.attr,
	&max_rate_attribute.attr,
	&weight_rate_attribute.attr,
	&weight_rtt_attribute.attr,
	&desired_rate_attribute.attr,
	&cycle_rtts_attribute.attr,
	&rb_per_cycle_attribute.attr,
	&max_rtt_gain_attribute.attr,
	NULL,
};


static struct kobj_type ktype = {
	.sysfs_ops = &sysfs_ops,
	.release = release,
	.default_attrs = default_attrs,
};


int mpcc_sysfs_register(struct mpcc_settings *settings, struct kset *set,
	unsigned int daddr, unsigned int dport, unsigned int lport,
	struct mpcc *m)
{
	int retval;

	memset(settings, 0, sizeof(*settings));
	settings->kobj.kset = set;

	retval = kobject_init_and_add(&settings->kobj, &ktype, NULL, "%lu", id_count);
	if (retval) {
		settings->has_kobj = false;
		kobject_put(&settings->kobj);
	} else {
		settings->has_kobj = true;
		kobject_uevent(&settings->kobj, KOBJ_ADD);
	}
	id_count++;

	settings->daddr = daddr;
	settings->dport = dport;
	settings->lport = lport;
	settings->cfg   = &m->cfg;

	if (settings->has_kobj)
		return 0;
	else
		return 1;
}


int mpcc_sysfs_unregister(struct mpcc_settings *settings)
{
	if (settings->has_kobj) {
		kobject_put(&settings->kobj);
	}

	return 0;
}
