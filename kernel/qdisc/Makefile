
QDEV := eth3
IPROUTE2 := ./iproute2
MPC_DIR = ../mpc

obj-m += mpcqd.o
mpcqd-objs += sch_mpc.o
mpcqd-y += $(MPC_DIR)/dfs.o $(MPC_DIR)/model.o $(MPC_DIR)/control.o \
	$(MPC_DIR)/sysfs.o
ccflags-y += -I$(shell realpath $(MPC_DIR)) -g -O0 -DDEBUG

all: #q_mpc.so
	#make -C "/lib/modules/$(shell uname -r)/build" M=$(PWD) modules
	make -C `nix-build -E '(import <nixpkgs> {}).linux.dev' --no-out-link`/lib/modules/*/build M=$(PWD) modules
	#make -C `nix-build -E '(import <nixpkgs> {}).linux_5_1.dev' --no-out-link`/lib/modules/*/build M=$(PWD) modules

#q_mpc.so: q_mpc.c
#	gcc -shared -o $@ $< -fPIC -I$(IPROUTE2)/include -I$(IPROUTE2)/tc

clean:
	#make -C "/lib/modules/$(shell uname -r)/build" M=$(PWD) clean
	make -C `nix-build -E '(import <nixpkgs> {}).linux.dev' --no-out-link`/lib/modules/*/build M=$(PWD) clean
	#make -C `nix-build -E '(import <nixpkgs> {}).linux_5_1.dev' --no-out-link`/lib/modules/*/build M=$(PWD) clean

start:
	insmod mpcqd.ko
	tc qdisc add dev $(QDEV) root mpc $(QARGS)

stop:
	tc qdisc del dev $(QDEV) root mpc
	rmmod mpcqd.ko

restart:
	make stop QDEV=$(QDEV)
	make -B
	make start QDEV=$(QDEV)
