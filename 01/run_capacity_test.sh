#!/bin/bash

# --- CONFIGURATION TEST ---
JMX_PLAN="CapacityTest.jmx"
DURATION=300
ITERATIONS=3

for i in $(seq 1 $ITERATIONS); do
    echo "==================================="
    echo "Starting Iteration $i of $ITERATIONS"
    echo "==================================="

    ssh antonio@192.168.64.3 "vmstat 1 300 > vmstat_iter_${i}.log" &
    VMSTAT_PID=$!

    jmeter -n -t "$JMX_PLAN" -l "results_iter_${i}.jtl" -e -o "report_html_iter_${i}"

    wait $VMSTAT_PID

    echo "Iteration $i completed. Log saved"
    echo " - JMeter report: report_html_iter_${i}/index.html"
    echo " - Log vmstat: vmstat_iter_${i}.log"
    echo ""

    sleep 10
done