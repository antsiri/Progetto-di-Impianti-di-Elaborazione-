"""
 * author Antonio Sirignano
 * created on 20-08-2026-16h-04m
 * github: https://github.com/antsiri
 * copyright 2026

Orchestrator of a full workload run.

Checks that the server is up, then launches as separate processes:
    * the LL metrics collector (``collector/metrics.py``);
    * the HL load generator (``load_gen/generator.py``);
and prints periodic progress messages until the run is complete.
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
    """
    Periodically print the run progress and detect clock drift.

    If the real gap between two checks is much larger than ``check_interval``
    the machine was probably suspended, which would invalidate the measures.

    Args:
        duration_seconds (int): expected run duration.
        check_interval (int): seconds between two progress messages.
        stop_event (threading.Event | None): stops the monitor when set.
        drift_threshold (float): drift (s) above which a warning is printed.
    """
    # monotonic clock: not affected by system clock changes
    start = time.monotonic()
    last_check = start

    while not (stop_event and stop_event.is_set()):
        time.sleep(check_interval)
        now = time.monotonic()

        # Drift = how much longer than expected the sleep actually lasted
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
    """
    Poll the ``/health`` endpoint until it answers 200 or ``timeout`` expires.

    Args:
        base_url (str): server base URL.
        timeout (int): maximum waiting time in seconds.

    Returns:
        bool: True if the server answered, False otherwise.
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(f"{base_url}/health", timeout=2)
            if resp.status_code == 200:
                return True
        except requests.RequestException:
            pass
        # Retry every half second
        time.sleep(0.5)
    return False


def run_full_workload(base_url: str, duration: int, threads: int,
                     ramp_up: int, interval: float, target_process: str,
                     hl_output: Path, ll_global_output: Path, ll_process_output: Path,
                     manifest_path: Path, manifest_type: str, think_time: float):
    """
    Run collector and load generator together and wait for both to finish.

    Args:
        base_url (str): server base URL.
        duration (int): load test duration (s).
        threads (int): number of load generator threads.
        ramp_up (int): ramp-up time (s).
        interval (float): collector sampling interval (s).
        target_process (str): name of the server process to monitor.
        hl_output (Path): HL report CSV.
        ll_global_output (Path): LL global metrics CSV.
        ll_process_output (Path): LL process metrics CSV.
        manifest_path (Path): resource manifest for the load generator.
        manifest_type (str): ``"tier"`` (real) or ``"synthetic"``.
        think_time (float): think time between requests (s).
    """
    print("Checking server availability...")
    if not check_server_alive(base_url):
        print(f"ERROR: server not reachable at {base_url}. Start it first.")
        sys.exit(1)
    print("Server is up")

    # The collector must cover both the ramp-up and the steady-state phase
    collector_duration = duration + ramp_up

    # Command lines of the two sub-processes (same Python interpreter)
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

    # Give the collector time to find the process and start sampling
    time.sleep(2)

    print("Starting load generator...")
    load_gen_proc = subprocess.Popen(load_gen_cmd)

    # Background thread that prints progress every 30 s
    stop_monitor = threading.Event()
    monitor_thread = threading.Thread(
        target=progess_monitor,
        args=(duration, 30, stop_monitor),
        daemon=True,
    )
    monitor_thread.start()

    # Wait for both sub-processes to terminate
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
    # Command-line interface
    parser = argparse.ArgumentParser(description="Orchestrate collector + load generator for a full workload run")
    parser.add_argument("--base-url", type=str, default="http://127.0.0.1:8000")
    parser.add_argument("--duration", type=int, default=300)  # as in the project document
    parser.add_argument("--threads", type=int, default=15)
    parser.add_argument("--ramp-up", type=int, default=15)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--target-process", type=str, default="uvicorn")
    parser.add_argument("--think-time", type=float, default=0.0)

    # Output files
    parser.add_argument("--hl-output", type=Path, default=Path("data/raw/hl_report.csv"))
    parser.add_argument("--ll-global-output", type=Path, default=Path("data/raw/ll_global.csv"))
    parser.add_argument("--ll-process-output", type=Path, default=Path("data/raw/ll_process.csv"))

    # Workload selection (real or synthetic)
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
