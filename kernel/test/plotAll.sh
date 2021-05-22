#!/bin/bash

if [[ -n $1 ]]
then
    dir=$1
else
    dir="."
fi

for file in $(find $dir -name '*-test.json')
do
    test=${file%-test.json}

    if [[ -e "$test-module.json"
        && ((! -e "$test-plot-test.pdf") || ($file -nt "$test-plot-test.pdf")) ]]
    then
        echo "Plotting $test"
        ./plot.py $test --output "$test-plot" --guess-id
    else
        echo "Skipping $test"
    fi
done
