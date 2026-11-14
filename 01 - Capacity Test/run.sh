#!/bin/bash
# =============================================================================
# Full capacity test driver (runs on the Mac / client side).
#
#   1. Setup:  copies setup_test.sh to the VM, generates the test files there,
#              publishes them under Apache and downloads the CSV list of files
#              used by the JMeter plan.
#   2. Test:   runs ITERATIONS JMeter iterations; during each one vmstat is
#              sampled on the VM, then its log is copied back locally.
# =============================================================================

# --- CONFIGURATION ---
VM_USER="antonio"
VM_IP="192.168.64.3"
JMX_PLAN="CapacityTest.jmx"
DURATION=300
ITERATIONS=3

echo "=========================================================="
echo " 1. SETUP PHASE (GENERATION AND SAVING FILES ON VM)"
echo "=========================================================="

# Copy the file-generation script to the VM
echo "[Mac -> VM] Sending script on vm..."
scp setup_test.sh ${VM_USER}@${VM_IP}:~/setup_test.sh

# Run it remotely: creates ~/files/*.dat and ~/file.csv
echo "[VM] File Generation..."
ssh ${VM_USER}@${VM_IP} "bash ~/setup_test.sh"

# Publish the generated files in the Apache document root
echo "[VM] Saving file on Apache (/var/www/html/files)..."
ssh ${VM_USER}@${VM_IP} "cp -r ~/files /var/www/html/"

# Download the CSV used by JMeter's CSV Data Set Config
echo "[VM -> Mac] Download di file.csv..."
scp ${VM_USER}@${VM_IP}:~/file.csv ./file.csv

echo "-> Setup completed!"
echo ""

echo "=========================================================="
echo " 2. STARTING CAPACITY TEST WITH JMETER ($ITERATIONS ITERATIONS OF ${DURATION}s)"
echo "=========================================================="

for i in $(seq 1 $ITERATIONS); do
    echo "----------------------------------------------------------"
    echo "Starting Iteration $i of $ITERATIONS"
    echo "----------------------------------------------------------"

    # Remove the outputs of a previous run (JMeter refuses a non-empty report dir)
    rm -f "results_iter_${i}.jtl"
    rm -rf "report_html_iter_${i}"

    # Start vmstat on the VM in background (1 sample/s for DURATION seconds)
    echo "[VM] Starting vmstat for $DURATION seconds..."
    ssh ${VM_USER}@${VM_IP} "vmstat 1 $DURATION > ~/vmstat_iter_${i}.log" &
    VMSTAT_PID=$!

    # Run JMeter in non-GUI mode: raw results in .jtl, HTML dashboard in report dir
    echo "[Mac] Starting JMeter CLI..."
    JVM_ARGS="-Xms2g -Xmx4g" jmeter -n -t "$JMX_PLAN" -l "results_iter_${i}.jtl" -e -o "report_html_iter_${i}"

    # Wait for the vmstat sampling to finish
    wait $VMSTAT_PID

    # Bring the vmstat log back to the local machine
    scp ${VM_USER}@${VM_IP}:~/vmstat_iter_${i}.log ./vmstat_iter_${i}.log

    echo "Iteration $i completed."
    echo " - Report JMeter: report_html_iter_${i}/index.html"
    echo " - Log vmstat salvato sulla VM in: ~/vmstat_iter_${i}.log"
    echo ""

    # Cool-down pause between consecutive iterations
    if [ $i -lt $ITERATIONS ]; then
        echo "10 seconds sleep"
        sleep 10
    fi
done

echo "=========================================================="
echo "   ALL TEST COMPLETED!      "
echo "=========================================================="
