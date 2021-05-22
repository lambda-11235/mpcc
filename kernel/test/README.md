
To run a test do
```
> ./run.sh TEST DEST [ LOGTIME ]
```

Where TEST is a name like `foo` or `bar/foo`. DEST is a destination server such
as `denv-pt1.es.net`. LOGTIME is how long to run the module logger for, in
seconds.  Note that setting LOGTIME can save you a lot of time, as its default
value is 120. Also, setting it too low will cutoff some of the data.

See [a list of
servers](https://fasterdata.es.net/performance-testing/perfsonar/esnet-perfsonar-services/esnet-iperf-hosts/).

To plot the data from a test run
```
> python plot.py TEST [ --title TITLE ] [ --output FILE ]
    [ --limit-quantile QUANT ]
```

Note that the times from BWCTL and the kernel modules don't line up. if
`limit-quantile` is set, then the plot makes the upper limit **double** that
quantile.
