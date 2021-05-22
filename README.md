
# Model Predictive Congestion Control

This repository contains code used in research on applying model
predictive control (MPC) theory to TCP congestion control.
Be warned that this is messy research code.
The following instructions should work, but a certain amount of work
may be required on the users end to understand and get the code
working.
Constructive feedback is welcome.


## Repository Structure

`src/`: Contains the main source code for the algorithm.  
`simulation/`: Contains code for running an event based network simulation.  
`kernel/mpc/`: Contains code for interfacing the algorithm to the Linux VFS.  
`kernel/tcp_cc/`: Contains the main Linux module code.


## Running a Simulation

To run a simulation, enter into the command line

```
> cd simulation
> mkdir build && cd build
> cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS='-march=native' ..
> make
> ./simulation
```

This should place simulation results in the `build/data/` directory.
The data can be plotted with the python scripts in `simulation/`.
Also, see `simulation/CMakeLists.txt` for options that control
simulation parameters.

The require python modules are
- matplotlib
- numpy
- pandas
- psutil
- seaborn
- tkinter


## Building the Kernel Module

First, you must install the linux kernel headers for your OS.
On Debian based systems this is done by installing a package called
`linux-headers`.
To build the kernel module and install it run

```
> cd kernel/tcp_cc
> make
> sudo insmod mpc_cc.ko
```

To make use the algorithm run

```
sudo sysctl net.ipv4.congestion_control=mpcc_cc
```


## Copyright

Copyright (C) 2020  University of California, Davis

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
