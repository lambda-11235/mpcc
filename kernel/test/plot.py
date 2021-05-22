#!/usr/bin/env python3

import argparse
import matplotlib

import matplotlib as mpl
import matplotlib.pyplot as plt

from data import Data

bwctlStartTime = 0

parser = argparse.ArgumentParser(description="Plots test results.")
parser.add_argument('test', type=str,
        help="The name of the test to run.")
parser.add_argument('-o', '--output', type=str,
        help="Sets output file base name.")
parser.add_argument('-e', '--output-extension', type=str, default="pdf",
        help="Sets the extension for output files (i.e. pdf, png, etc.).")
parser.add_argument('-q', '--limit-quantile', type=float,
        help="Limits output range to within double of a certain quantile.")
parser.add_argument('-s', '--stream', type=int, default=0,
        help="Select the iperf stream to use.")
parser.add_argument('-a', '--all-modules', action='store_true',
        help="Plot all module data.")
parser.add_argument('-i', '--with-id', type=int, default=None,
        help="Plot all module data with a certain id.")
args = parser.parse_args()


data = Data(args.test)

stream = data.streams[args.stream]

sk = stream.socket.mode()[0]
c = data.connections.query("socket == @sk")

if args.all_modules:
    module = data.module
elif args.with_id is not None:
    q = 'id == "' + str(args.with_id) + '"'
    module = data.module.query(q)
else:
    lport = c.local_port.iloc[0]
    q = 'lport == ' + str(lport)
    module = data.module.query(q)

stream.sort_values('start', inplace=True)
module.sort_values('time', inplace=True)

print(stream.describe())
print(module.describe())


mpl.style.use('seaborn-bright')
mpl.rc('figure', dpi=200)


### Rate ###
stream.bits_per_second /= 2**20
module.set_rate *= module.INT_BPS/2**17
module.rb_max *= module.INT_BPS/2**17
module.rb *= module.INT_BPS/2**17

fig = plt.figure()
ax = fig.add_subplot(111)


ax.plot('time', 'rb', data=module, label="rB", color="red")
ax.plot('time', 'set_rate', data=module, label="Set Rate", color="green")
ax.plot('start', 'bits_per_second', data=stream, label="Observed Rate", color="blue")

ax.set_xlabel("Time (s)")
ax.set_ylabel("Rate (Mbps)")
ax.legend()

#fig.savefig(args.output_prefix + "-cwnd.png", bbox_inches='tight')


### RTT ###
stream.rtt /= 1e3
module.target_rtt /= 1e3
module.lp /= 1e3
module.lb /= 1e3
module.rtt_avg /= 1e3

fig = plt.figure()
ax = fig.add_subplot(111)

lower = module['lp'].quantile(0.1)
upper = module['lb'].quantile(0.9)
delta = (upper - lower)/4
#ax.set_ylim(lower - delta, upper + delta)

ax.plot('time', 'rtt_avg', '--', data=module, label="RTT Avg.", color="yellow")

ax.plot('start', 'rtt', data=stream, label="Observed RTT", color="blue")
ax.plot('time', 'target_rtt', data=module, label="Target RTT", color="green")
ax.plot('time', 'lp', data=module, label="lP", color="orange")
ax.plot('time', 'lb', data=module, label="lB", color="red")

ax.set_xlabel("Time (s)")
ax.set_ylabel("RTT (ms)")
ax.legend()


## Losses
fig = plt.figure()
ax = fig.add_subplot(111)

ax.plot('start', 'retransmits', data=stream, label="Losses", color="red")

ax.set_xlabel("Time (s)")
ax.set_ylabel("Losses")
ax.legend()


plt.show()
