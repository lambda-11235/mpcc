#!/usr/bin/env python3

import argparse
import ipaddress
import json
import subprocess
import os
import psutil
import time
import socket

import logger
import rate

parser = argparse.ArgumentParser(description = "Run a test.")
parser.add_argument('test', type=str,
        help="The test to run.")
parser.add_argument('destination', type=str,
        help="The destination server address.")
parser.add_argument('-r', '--rate', type=int, nargs=2, action='append',
        help="Max/min pacing rate in mbps for one stream. (sysfs API only)")
parser.add_argument('-a', '--all-ports', action='store_true',
        help="When setting min/max rates, apply to all ports on system.")
parser.add_argument('-P', '--parallel', type=int, default=1,
        help="When setting min/max rates, apply to all ports on system.")
parser.add_argument('-d', '--duration', type=int, default=60,
        help="Logging duration in seconds.")
parser.add_argument('-i', '--interval', type=float, default=0.1,
        help="Interval between samples.")
parser.add_argument('-t', '--tester', type=str, choices=['iperf3', 'psched'],
        default='iperf3', help="The tester to run.")
parser.add_argument('-C', '--cong-control', type=str,
        help="Congestion control algorithm to use.")
parser.add_argument('-v', '--verbose', action='store_true',
        help="Print additional information.")
args = parser.parse_args()


dest = int(ipaddress.ip_address(socket.gethostbyname(args.destination)))
ports = range(5200, 5300)

print("Starting kernel logging.")
logger = logger.Logger(args.test + "-module.json", args.interval, args.verbose)
logger.start()


with open(args.test + "-test.json", mode = 'w') as testFile:
    print("Starting tester.")

    if args.tester == 'iperf3':
        comLine = ['iperf3', '-c', args.destination,
            '-i', str(args.interval), '-t', str(args.duration), '-J',
            '-P', str(args.parallel)]

        if args.cong_control is not None:
            comLine += ['-C', args.cong_control]

        tester = psutil.Popen(comLine,
            stdout = testFile)

        rateSetter = rate.RateSysfs(args.rate, dest, ports, allPorts=args.all_ports)
        rateSetter.start()

        tester.wait()
        print("Tester finished with code {}.".format(tester.returncode))

        rateSetter.stop()
    elif args.tester == 'psched':
        comLine = ['pscheduler', 'task', '--tool', 'iperf3',
            '--format=json', 'throughput',
            '--dest', args.destination,
            '-i', str(args.interval),
            '-t', str(args.duration),
            '-P', str(args.parallel)]

        if args.cong_control is not None:
            comLine += ['--congestion={}'.format(args.cong_control)]

        tester = psutil.Popen(comLine,
            stdout = subprocess.PIPE)

        # Set rate for every port since I can't figure out how to get
        # pscheduler's ports.
        rateSetter = rate.RateSysfs(args.rate, dest, ports, allPorts=args.all_ports)
        rateSetter.start()

        (output, _) = tester.communicate()
        print("Tester finished with code {}.".format(tester.returncode))

        rateSetter.stop()

        if output != "":
            diags = json.loads(output.splitlines()[0])['diags']
            diags = diags.split('Participant')[1]
            diags = diags[diags.find('\n\n'):]

            with open(args.test + '-test.json', 'w') as f:
                #f.write(json.dumps(js, indent=4))
                f.write(diags)
        else:
            print("BWCTL failed to produce output.")
    else:
        print("Unrecognized tester " + args.tester + ".")

print("Stopping kernel logging")
logger.stop()
