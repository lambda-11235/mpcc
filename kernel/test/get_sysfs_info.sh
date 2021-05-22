#!/bin/sh

for f in /sys/kernel/mpccc/*
do
	printf '%d->%d:%d\n' `cat $f/lport` `cat $f/daddr` `cat $f/dport`
	printf '\tweight = %d\n' `cat $f/weight`
	printf '\tlearn_rate = %d\n' `cat $f/learn_rate`
	printf '\tover = %d\n' `cat $f/over`
	printf '\tmin_rate = %d\n' `cat $f/min_rate`
	printf '\tmax_rate = %d\n' `cat $f/max_rate`
	printf '\tc1 = %d\n' `cat $f/c1`
	printf '\tc2 = %d\n' `cat $f/c2`
done
