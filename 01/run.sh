#!/bin/bash

# --- CONFIGURATION ---
VM_USER="antonio"
VM_IP="192.168.64.3"
JMX_PLAN="CapacityTest.jmx"
DURATION=300
ITERATIONS=3

echo "=========================================================="
echo " 1. SETUP PHASE (GENERATION AND SAVING FILES ON VM)"
echo "=========================================================="

echo "[Mac -> VM] Sending script on vm..."
scp setup_test.sh ${VM_USER}@${VM_IP}:~/setup_test.sh

echo "[VM] File Generation..."
ssh ${VM_USER}@${VM_IP} "bash ~/setup_test.sh"

echo "[VM] Saving file on Apache (/var/www/html/files)..."
ssh ${VM_USER}@${VM_IP} "cp -r ~/files /var/www/html/"

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

    rm -f "results_iter_${i}.jtl"
    rm -rf "report_html_iter_${i}"

    echo "[VM] Starting vmstat for $DURATION seconds..."
    ssh ${VM_USER}@${VM_IP} "vmstat 1 $DURATION > ~/vmstat_iter_${i}.log" &
    VMSTAT_PID=$!

    echo "[Mac] Starting JMeter CLI..."
    JVM_ARGS="-Xms2g -Xmx4g" jmeter -n -t "$JMX_PLAN" -l "results_iter_${i}.jtl" -e -o "report_html_iter_${i}"

    wait $VMSTAT_PID

    scp ${VM_USER}@${VM_IP}:~/vmstat_iter_${i}.log ./vmstat_iter_${i}.log

    echo "Iteration $i completed."
    echo " - Report JMeter: report_html_iter_${i}/index.html"
    echo " - Log vmstat salvato sulla VM in: ~/vmstat_iter_${i}.log"
    echo ""

    if [ $i -lt $ITERATIONS ]; then
        echo "10 seconds sleep"
        sleep 10
    fi
done

echo "=========================================================="
echo "   ALL TEST COMPLETED!      "
echo "=========================================================="