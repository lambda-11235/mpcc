
QDEV := eth3
MPC_DIR = ../mpc
SRC_DIR = ../../src

obj-m += mpc_cc.o
mpc_cc-y += cong_control.o
mpc_cc-y += $(SRC_DIR)/mpcc.o $(SRC_DIR)/filter.o $(MPC_DIR)/dfs.o $(MPC_DIR)/sysfs.o
ccflags-y += -I$(shell realpath $(MPC_DIR)) -DLINUX_KERNEL
ccflags-y += -g -O0 -DDEBUG

all:
	make -C "/lib/modules/$(shell uname -r)/build" M=$(PWD) modules
	#make -C `nix-build -E '(import <nixpkgs> {}).linux.dev' --no-out-link`/lib/modules/*/build M=$(PWD) modules
	#make -C `nix-build -E '(import <nixpkgs> {}).linux_latest.dev' --no-out-link`/lib/modules/*/build M=$(PWD) modules

clean:
	make -C "/lib/modules/$(shell uname -r)/build" M=$(PWD) clean
	#make -C `nix-build -E '(import <nixpkgs> {}).linux.dev' --no-out-link`/lib/modules/*/build M=$(PWD) clean
	#make -C `nix-build -E '(import <nixpkgs> {}).linux_latest.dev' --no-out-link`/lib/modules/*/build M=$(PWD) clean

start:
	insmod mpc_cc.ko
	tc qdisc replace dev $(QDEV) root fq
	sysctl -w net.ipv4.tcp_congestion_control=mpc_cc

stop:
	sysctl -w net.ipv4.tcp_congestion_control=cubic
	tc qdisc del dev $(QDEV) root
	rmmod mpc_cc

restart:
	make stop QDEV=$(QDEV)
	make -B
	make start QDEV=$(QDEV)
