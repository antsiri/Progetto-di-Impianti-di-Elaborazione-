"""
 * author Antonio Sirignano
 * created on 19-08-2026-07h-57m
 * github: https://github.com/antsiri
 * copyright 2026

Low-level (LL) metrics collector based on psutil.

At a fixed interval it samples:
    * system-wide metrics (CPU, memory, swap, disk and network I/O deltas)
      -> ``ll_global.csv``;
    * metrics of the monitored server process (CPU, RSS/VMS, threads,
      file descriptors, I/O bytes) -> ``ll_process.csv``.
"""

import csv
import time
import psutil
import argparse

from pathlib import Path
from datetime import datetime, timezone


# CSV columns of the system-wide report
GLOBAL_FIELDS = [
    "timestamp", "cpu_percent", "mem_total", "mem_available", "mem_used",
    "mem_free", "mem_percent", "swap_used", "swap_free", "swap_percent",
    "disk_read_bytes_delta", "disk_write_bytes_delta",
    "net_bytes_sent_delta", "net_bytes_recv_delta",
]

# CSV columns of the per-process report
PROCESS_FIELDS = [
    "timestamp", "pid", "proc_cpu_percent", "proc_rss", "proc_vms",
    "proc_num_threads", "proc_num_fds", "proc_io_read_bytes", "proc_io_write_bytes",
]


def collect_global_snapshot(prev_counters: dict | None):
    """
    Take one snapshot of the system-wide metrics.

    Disk and network counters are cumulative, so the difference with the
    previous snapshot is stored (bytes transferred in the last interval).

    Args:
        prev_counters (dict | None): cumulative counters of the previous
            snapshot (None on the first call -> deltas are 0).

    Returns:
        tuple[dict, dict]: the snapshot row (``GLOBAL_FIELDS``) and the
        current cumulative counters to pass to the next call.
    """
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    disk = psutil.disk_io_counters()
    net = psutil.net_io_counters()

    # Current cumulative counters (disk counters may be unavailable -> 0)
    current = {
        "disk_read_bytes": disk.read_bytes if disk else 0,
        "disk_write_bytes": disk.write_bytes if disk else 0,
        "net_bytes_sent": net.bytes_sent,
        "net_bytes_recv": net.bytes_recv,
    }

    # Deltas with respect to the previous sample
    if prev_counters is None:
        deltas = {k: 0 for k in current}
    else:
        deltas = {k: current[k] - prev_counters[k] for k in current}

    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        # interval=None: CPU usage since the previous call (non-blocking)
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
    """
    Take one snapshot of the metrics of a single process.

    Args:
        proc (psutil.Process): process to inspect.

    Returns:
        dict: row with the ``PROCESS_FIELDS`` columns (I/O and fd values are
        None when not supported by the OS or not accessible).
    """
    # oneshot() caches process info so the multiple reads below are faster
    with proc.oneshot():
        mem = proc.memory_info()

        # io_counters is not available on every platform (e.g. macOS)
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
    """
    Find the first running process whose name or command line contains
    ``name_substring`` (case-insensitive).

    Args:
        name_substring (str): text to look for (e.g. ``"uvicorn"``).

    Returns:
        psutil.Process: the matching process.

    Raises:
        ProcessLookupError: if no process matches.
    """
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            name = proc.info.get('name')
            cmdline = proc.info.get('cmdline') or []

            # Match on the process name...
            if name and name_substring.lower() in name.lower():
                return proc
            # ...or on any argument of the command line (e.g. "python -m uvicorn")
            if any(name_substring.lower() in arg.lower() for arg in cmdline):
                return proc

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    raise ProcessLookupError(f"No process in execution founded containing: '{name_substring}'")


def run_collector(proc: psutil.Process, duration_seconds: int,
                  interval_seconds: float, global_out: Path,
                  process_out: Path,
                  ):
    """
    Sample global and process metrics for ``duration_seconds`` seconds and
    write them to two CSV files.

    Args:
        proc (psutil.Process): process to monitor.
        duration_seconds (int): total monitoring time.
        interval_seconds (float): time between two samples.
        global_out (Path): CSV for system-wide metrics.
        process_out (Path): CSV for process metrics.
    """

    global_out.parent.mkdir(parents=True, exist_ok=True)
    process_out.parent.mkdir(parents=True, exist_ok=True)

    with open(global_out, "w", newline="") as gf, open(process_out, "w", newline="") as pf:
        g_writer = csv.DictWriter(gf, fieldnames=GLOBAL_FIELDS)
        p_writer = csv.DictWriter(pf, fieldnames=PROCESS_FIELDS)
        g_writer.writeheader()
        p_writer.writeheader()

        # Prime the CPU counters: the first cpu_percent(None) call always returns 0
        psutil.cpu_percent(interval=None)
        proc.cpu_percent(interval=None)
        time.sleep(interval_seconds)

        prev_counters = None
        elapsed = 0.0
        while elapsed < duration_seconds:
            snapshot, prev_counters = collect_global_snapshot(prev_counters)
            g_writer.writerow(snapshot)
            p_writer.writerow(collect_process_snapshot(proc))
            # Flush every sample so data is not lost if the collector is killed
            gf.flush()
            pf.flush()

            time.sleep(interval_seconds)
            elapsed += interval_seconds


if __name__ == "__main__":
    # Command-line interface
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
        # Locate the server process, then start sampling
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
