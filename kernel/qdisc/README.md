
# Sample QDisc

This is a sample qdisc I'm using for testing. `sch_hi.*` and `module.c` contain
the code for the kernel module. `q_hi.c` is a plugin for the `tc` command to
support passing arguments to the kernel module. Currently no arguments are
supported. The outputted `q_hi.so` file must be put on the path for `TC_LIB_DIR`,
which by default is `/usr/lib/tc`.

## Building

First obtain the appropriate submodules by running `git submodule init` and then
`git submodule update`. This fetches the source for iproute2, which is used to
build `q_hi.so`.

## Running

To install the qdisc run `make start`. This runs the following

```
insmod hiqd.ko
tc qdisc add dev enp3s0 root hi
```

`make stop` similarly removes the qdisc. If enp3s0 is the wrong device, then set
QDEV to the appropriate on (`make start QDEV=<dev>`). Additionally, QARGS can
be set to send arguments to the QDisc.
