
QDEV := eth3

obj-m += cwnd_tester.o
cwnd_tester-y += cong_control.o
ccflags-y += -g -O0 -DDEBUG

all:
	make -C "/lib/modules/$(shell uname -r)/build" M=$(PWD) modules

clean:
	make -C "/lib/modules/$(shell uname -r)/build" M=$(PWD) clean

start:
	insmod cwnd_tester.ko
	tc qdisc replace dev $(QDEV) root fq
	sysctl -w net.ipv4.tcp_congestion_control=cwnd_tester

stop:
	sysctl -w net.ipv4.tcp_congestion_control=cubic
	tc qdisc del dev $(QDEV) root
	rmmod cwnd_tester

restart:
	make stop QDEV=$(QDEV)
	make -B
	make start QDEV=$(QDEV)
