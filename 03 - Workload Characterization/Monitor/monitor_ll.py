"""
 * author Antonio Sirignano
 * created on 03-10-2026-08h-22m
 * github: https://github.com/antsiri
 * copyright 2026

Low-level monitor based on psutil that writes a vmstat-like report.

Every INTERVAL seconds, for DURATION seconds, it writes one line with the
same 17 columns as vmstat (fields not available through psutil are 0), so
the same parsers can be used for real and synthetic reports.
"""

import time
import psutil

# Output report, sampling interval (s) and total duration (s)
OUTPUT_FILE = "report_LL_synthetic.txt"
INTERVAL = 1
DURATION = 900

print(f"Starting monitoring Low-Level for {DURATION} seconds...")

with open(OUTPUT_FILE, "w") as f:
    # vmstat-compatible header
    f.write("r b swpd free buff cache si so bi bo in cs us sy id wa st\n")

    psutil.cpu_percent(interval=None)                               #Initialize CPU counters

    start_time = time.time()
    while time.time() - start_time < DURATION:
        mem = psutil.virtual_memory()                               #Memory metrics
        swap = psutil.swap_memory()

        # Blocking call: waits INTERVAL seconds, so it also paces the loop
        cpu_times = psutil.cpu_times_percent(interval=INTERVAL)     #CPU metrics (perccentage)
        us = cpu_times.user
        sy = cpu_times.system
        id_val = cpu_times.idle
        wa = getattr(cpu_times, 'iowait', 0.0)

        ctx_switches = psutil.cpu_stats().ctx_switches              #System metrics and I/O

        # Memory values converted to KB as in vmstat; unavailable fields set to 0
        row = f"0 0 {swap.used // 1024} {mem.free // 1024} {getattr(mem, 'buffers', 0) // 1024} {getattr(mem, 'cached', 0) // 1024} 0 0 0 0 0 {ctx_switches} {us:.1f} {sy:.1f} {id_val:.1f} {wa:.1f} 0.0\n"
        f.write(row)
        f.flush()


print('Monitoring completed...')
