"""
 * author Antonio Sirignano
 * created on 20-08-2026-16h-04m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import argparse
import subprocess
import sys
import time 
import requests
import threading

from pathlib import Path

def progess_monitor(duration_seconds: int, check_interval: int = 30, stop_event: threading.Event = None, 
                    drift_threshold: float = 5.0):
    start = time.monotonic()
    last_check = start

    while not (stop_event and stop_event.is_set()):
        time.sleep(check_interval)
        now = time.monotonic()

        actual_gap = now - last_check
        expected_gap = check_interval
        drift = actual_gap - expected_gap

        elapsed_total = now - start
        remaining = max(0, duration_seconds - elapsed_total)
        pct = min(100, elapsed_total / duration_seconds * 100)

        status = f"[PROGRESS] {pct:5.1f}% - elapsed: {elapsed_total/60:.1f} min, {remaining/60:.1f} min"

        if drift > drift_threshold:
            status += f"WARNING: drift releveted: {drift:.1f}s (possible system sleep/suspension)."

        print(status)
        last_check = now

        if elapsed_total >= duration_seconds:
            break

def check_server_alive(base_url: str, timeout: int = 10) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(f"{base_url}/health", timeout=2)
            if resp.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.5)
    return False

def run_full_workload(base_url: str, duration: int, threads: int,
                     ramp_up: int, interval: float, target_process: str,
                     hl_output: Path, ll_global_output: Path, ll_process_output: Path,
                     manifest_path: Path, manifest_type: str, think_time: float):
    print("Checking server availability...")
    if not check_server_alive(base_url):
        print(f"ERROR: server not reachable at {base_url}. Start it first.")
        sys.exit(1)
    print("Server is up")

    collector_duration = duration + ramp_up

    collector_cmd = [
        sys.executable, "collector/metrics.py",
        "--target", target_process,
        "--duration", str(collector_duration),
        "--interval", str(interval),
        "--global-out", str(ll_global_output),
        "--process-out", str(ll_process_output),
    ]

    load_gen_cmd = [
        sys.executable, "load_gen/generator.py",
        "--base-url", base_url,
        "--threads", str(threads),
        "--duration", str(duration),
        "--ramp-up", str(ramp_up),
        "--output", str(hl_output),
        "--manifest", str(manifest_path),
        "--manifest-type", manifest_type,
        "--think-time", str(think_time),
    ]

    print(f"Workload type: {manifest_type} (manifest: {manifest_path})")
    print("Starting collector...")
    collector_proc = subprocess.Popen(collector_cmd)

    time.sleep(2)

    print("Starting load generator...")
    load_gen_proc = subprocess.Popen(load_gen_cmd)

    stop_monitor = threading.Event()
    monitor_thread = threading.Thread(
        target=progess_monitor,
        args=(duration, 30, stop_monitor),
        daemon=True,
    )
    monitor_thread.start()

    load_gen_proc.wait()
    stop_monitor.set()
    print("Load generator finished.")

    collector_proc.wait()
    print("Collector finished.")

    print("Full workload run completed.")
    print(f"    HL Report:          {hl_output}")
    print(f"    LL Global Report:   {ll_global_output}")
    print(f"    LL Process Report:  {ll_process_output}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orchestrate collector + load generator for a full workload run")
    parser.add_argument("--base-url", type=str, default="http://127.0.0.1:8000")
    parser.add_argument("--duration", type=int, default=300)  # come nel documento
    parser.add_argument("--threads", type=int, default=15)
    parser.add_argument("--ramp-up", type=int, default=15)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--target-process", type=str, default="uvicorn")
    parser.add_argument("--think-time", type=float, default=0.0)

    parser.add_argument("--hl-output", type=Path, default=Path("data/raw/hl_report.csv"))
    parser.add_argument("--ll-global-output", type=Path, default=Path("data/raw/ll_global.csv"))
    parser.add_argument("--ll-process-output", type=Path, default=Path("data/raw/ll_process.csv"))

    parser.add_argument("--manifest", type=Path, default=Path("server/static/manifest.csv"),
                        help="Path al manifest: manifest.csv (tier) o synthetic_workload_weighted.csv (synthetic)")
    parser.add_argument("--manifest-type", type=str, choices=["tier", "synthetic"], default="tier",
                        help="'tier': workload reale (pool pesata per categoria dimensionale). "
                             "'synthetic': workload sintetico (pool pesata da clustering HL).")

    args = parser.parse_args()

    run_full_workload(
        base_url=args.base_url,
        duration=args.duration,
        threads=args.threads,
        ramp_up=args.ramp_up,
        interval=args.interval,
        target_process=args.target_process,
        hl_output=args.hl_output,
        ll_global_output=args.ll_global_output,
        ll_process_output=args.ll_process_output,
        manifest_type=args.manifest_type, 
        manifest_path=args.manifest,
        think_time=args.think_time
    )