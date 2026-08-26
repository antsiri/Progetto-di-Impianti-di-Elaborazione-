"""
 * author Antonio Sirignano
 * created on 19-08-2026-07h-57m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import csv
import time
import psutil
import argparse

from pathlib import Path
from datetime import datetime, timezone


GLOBAL_FIELDS = [
    "timestamp", "cpu_percent", "mem_total", "mem_available", "mem_used",
    "mem_free", "mem_percent", "swap_used", "swap_free", "swap_percent",
    "disk_read_bytes_delta", "disk_write_bytes_delta",
    "net_bytes_sent_delta", "net_bytes_recv_delta",
]

PROCESS_FIELDS = [
    "timestamp", "pid", "proc_cpu_percent", "proc_rss", "proc_vms",
    "proc_num_threads", "proc_num_fds", "proc_io_read_bytes", "proc_io_write_bytes",
]


def collect_global_snapshot(prev_counters: dict | None):
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    disk = psutil.disk_io_counters()
    net = psutil.net_io_counters()

    current = {
        "disk_read_bytes": disk.read_bytes if disk else 0,
        "disk_write_bytes": disk.write_bytes if disk else 0,
        "net_bytes_sent": net.bytes_sent,
        "net_bytes_recv": net.bytes_recv,
    }

    if prev_counters is None:
        deltas = {k: 0 for k in current}
    else:
        deltas = {k: current[k] - prev_counters[k] for k in current}

    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu_percent": psutil.cpu_percent(interval=None),
        "mem_total": vm.total,
        "mem_available": vm.available,
        "mem_used": vm.used,
        "mem_free": vm.free,
        "mem_percent": vm.percent,
        "swap_used": sw.used,
        "swap_free": sw.free,
        "swap_percent": sw.percent,
        "disk_read_bytes_delta": deltas["disk_read_bytes"],
        "disk_write_bytes_delta": deltas["disk_write_bytes"],
        "net_bytes_sent_delta": deltas["net_bytes_sent"],
        "net_bytes_recv_delta": deltas["net_bytes_recv"],
        }
    
    return snapshot, current

def collect_process_snapshot(proc: psutil.Process):
    with proc.oneshot():
        mem = proc.memory_info()

        io_read = None
        io_write = None
        if hasattr(proc, "io_counters"):
            try:
                io = proc.io_counters()
                io_read = io.read_bytes
                io_write = io.write_bytes
            except (psutil.AccessDenied, NotImplementedError):
                pass

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pid": proc.pid,
            "proc_cpu_percent": proc.cpu_percent(interval=None),
            "proc_rss": mem.rss,
            "proc_vms": mem.vms,
            "proc_num_threads": proc.num_threads(),
            "proc_num_fds": proc.num_fds() if hasattr(proc, "num_fds") else None,
            "proc_io_read_bytes": io_read,
            "proc_io_write_bytes": io_write,
        }


def find_process_by_name(name_substring: str) -> psutil.Process:
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            name = proc.info.get('name')
            cmdline = proc.info.get('cmdline') or []

            if name and name_substring.lower() in name.lower():
                return proc
            if any(name_substring.lower() in arg.lower() for arg in cmdline):
                return proc

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    raise ProcessLookupError(f"No process in execution founded containing: '{name_substring}'")


def run_collector(proc: psutil.Process, duration_seconds: int,
                  interval_seconds: float, global_out: Path,
                  process_out: Path,
                  ):

    global_out.parent.mkdir(parents=True, exist_ok=True)
    process_out.parent.mkdir(parents=True, exist_ok=True)
    
    with open(global_out, "w", newline="") as gf, open(process_out, "w", newline="") as pf:
        g_writer = csv.DictWriter(gf, fieldnames=GLOBAL_FIELDS)
        p_writer = csv.DictWriter(pf, fieldnames=PROCESS_FIELDS)
        g_writer.writeheader()
        p_writer.writeheader()

        psutil.cpu_percent(interval=None)
        proc.cpu_percent(interval=None)
        time.sleep(interval_seconds)

        prev_counters = None
        elapsed = 0.0
        while elapsed < duration_seconds:
            snapshot, prev_counters = collect_global_snapshot(prev_counters)
            g_writer.writerow(snapshot)
            p_writer.writerow(collect_process_snapshot(proc))
            gf.flush()
            pf.flush()

            time.sleep(interval_seconds)
            elapsed += interval_seconds


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="System and process metrics collector using psutil")

    parser.add_argument("-t", "--target", type=str, default="uvicorn",
                        help="Process substring name or command to monitor (default: 'uvicorn')")
    parser.add_argument("-d", "--duration", type=int, default=300,
                        help="Monitoring duration in seconds (default: 300)")
    parser.add_argument("-i", "--interval", type=float, default=1.0,
                        help="Interval between relevetions in seconds (default: 1.0)")

    parser.add_argument("--global-out", type=Path, default=Path("data/raw/ll_global.csv"),
                        help="Destination path for global metrics")
    parser.add_argument("--process-out", type=Path, default=Path("data/raw/ll_process.csv"),
                            help="Destination path for process metrics")

    args = parser.parse_args()

    try:
        print(f"Finding the process: '{args.target}' in progress...")
        target_proc = find_process_by_name(args.target)
        print(f"Process found: PID {target_proc.pid} (Cmd: {' '.join(target_proc.cmdline()[:3])}...)")
        print(f"Starting monitoring for {args.duration} seconds. Interval: {args.interval}s")

        run_collector(
            proc=target_proc,
            duration_seconds=args.duration,
            interval_seconds=args.interval,
            global_out=args.global_out,
            process_out=args.process_out,
        )

        print("Monitoring completed with success.")

    except ProcessLookupError as e:
        print(f"Error: {e}")
        print("Make sure the server is started and running")
    except KeyboardInterrupt:
        print("User interrupts")