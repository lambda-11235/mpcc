set term pdf font ",22"

csvFile = ARG1
set datafile separator ","
set xrange [*:*] noextend
unset key

gt0(x) = x > 0 ? x : 1/0

set xlabel "Time (s)"

set output sprintf("%s-rate.pdf", ARG2)
set ylabel "Rate (Gbps)"
plot [] [0:10] csvFile using 1:($2/(1<<30)) with lines lc rgb "blue"

set output sprintf("%s-rtt.pdf", ARG2)
set ylabel "RTT (ms)"
plot [] [20:30] csvFile using 1:($3/1000) with lines lc rgb "blue"

set output sprintf("%s-drops.pdf", ARG2)
set ylabel "Drops"
plot csvFile using 1:4 with lines lc rgb "red"
