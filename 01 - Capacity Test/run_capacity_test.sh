#!/bin/bash
# =============================================================================
# Minimal capacity test loop (no setup phase).
# For each iteration: samples vmstat on the VM while JMeter runs the test plan
# in non-GUI mode, then waits 10 s before the next iteration.
# =============================================================================

# --- CONFIGURATION TEST ---
JMX_PLAN="CapacityTest.jmx"
DURATION=300
ITERATIONS=3

for i in $(seq 1 $ITERATIONS); do
    echo "==================================="
    echo "Starting Iteration $i of $ITERATIONS"
    echo "==================================="

    # Start vmstat on the VM in background (1 sample/s for 300 s)
    ssh antonio@192.168.64.3 "vmstat 1 300 > vmstat_iter_${i}.log" &
    VMSTAT_PID=$!

    # Run the JMeter test plan and generate the HTML report
    jmeter -n -t "$JMX_PLAN" -l "results_iter_${i}.jtl" -e -o "report_html_iter_${i}"

    # Wait until vmstat has finished sampling
    wait $VMSTAT_PID

    echo "Iteration $i completed. Log saved"
    echo " - JMeter report: report_html_iter_${i}/index.html"
    echo " - Log vmstat: vmstat_iter_${i}.log"
    echo ""

    # Cool-down pause between iterations
    sleep 10
done
