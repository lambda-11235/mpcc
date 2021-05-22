#!/bin/sh

set -ex

if [ $# -lt 3 ]
then
    echo "Usage: $0 testdir host reps [run.py args...]"
    exit 1
fi

testdir=$(realpath $1)
base=$(realpath ..)
host=$2
reps=$3

shift 3


for cc in illinois reno vegas bbr htcp mpcc_cc
do
    sysctl net.ipv4.tcp_congestion_control=$cc

    for rep in `seq 1 $reps`
    do
        ./run.py $testdir/$cc-$rep $host $@
    done
done
