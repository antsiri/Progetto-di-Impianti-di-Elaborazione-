"""
 * author Antonio Sirignano
 * created on 19-08-2026-09h-57m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import csv
import time 
import random
import argparse
import threading
import requests

from pathlib import Path
from queue import Queue, Empty
from datetime import datetime, timezone

HL_FIELDS = [
    "timeStamp", "elapsed", "label", "responseCode", "threadName",
    "bytes", "URL", "latency", "success",
]

DEFAULT_TIER_WEIGHTS = {
    "low": 5,
    "mid_low": 4,
    "mid": 3,
    "mid_high": 2,
    "high": 1,
}

def load_manifest(manifest_path: Path):
    resources = []
    with open(manifest_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            resources.append(row)

    return resources

def build_weighted_pool(resources, tier_weights):
    pool = []
    for r in resources:
        weight = tier_weights.get(r["tier"], 1)
        pool.extend([r] * weight)

    return pool

def worker(worker_id: int, base_url: str, pool: list,
           stop_event: threading.Event, result_queue: Queue, think_time: float = 0.0):
    thread_name = f"Group-{worker_id}"
    session = requests.Session()

    while not stop_event.is_set():
        resource = random.choice(pool)
        url = f"{base_url}/samples/{resource['filename']}"

        timestamp = datetime.now(timezone.utc).isoformat()
        start = time.perf_counter()

        try:
            resp = session.get(url=url, timeout=10, stream=True)
            latency_ms = (time.perf_counter() - start) * 1000

            content = resp.content
            elapsed_ms = (time.perf_counter() - start) * 1000

            result_queue.put({
                "timeStamp": timestamp,
                "elapsed": round(elapsed_ms, 3),
                "label": resource["filename"],
                "responseCode": resp.status_code,
                "threadName": thread_name,
                "bytes": len(content),
                "URL": url,
                "latency": round(latency_ms, 3),
                "success": resp.status_code == 200,
            })
        except requests.RequestException as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            result_queue.put({
                "timeStamp": timestamp,
                "elapsed": round(elapsed_ms, 3),
                "label": resource["filename"],
                "responseCode": None,
                "threadName": thread_name,
                "bytes": 0,
                "URL": url,
                "latency": None,
                "success": False,
            })

        if think_time > 0:
            time.sleep(think_time)

def writer_loop(result_queue: Queue, output_path: Path, stop_event: threading.Event):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=HL_FIELDS)
        writer.writeheader()
        while not (stop_event.is_set() and result_queue.empty()):   
            try:
                row = result_queue.get(timeout=0.5)
                writer.writerow(row)
                f.flush()         
            except Empty:
                continue

def run_load_test(base_url: str, manifest_path: Path, num_threads: int,
                  duration_seconds: int, ramp_up_seconds: int, output_path: Path,
                  tier_weights: dict, think_time: float, manifest_type: str
                  ):

    if manifest_type == "tier":
        resources = load_manifest(args.manifest)
        pool = build_weighted_pool(resources, DEFAULT_TIER_WEIGHTS)
    else:  # synthetic
        resources = load_synthetic_manifest(args.manifest)
        pool = build_weighted_pool_from_synthetic(resources)
    

    result_queue = Queue()
    stop_event = threading.Event()

    writer_thread = threading.Thread(
        target=writer_loop,
        args=(result_queue, output_path, stop_event)
    )
    writer_thread.start()

    workers = []
    delay_between_threads = ramp_up_seconds / num_threads if num_threads > 0 else 0

    for i in range(num_threads):
        t = threading.Thread(
            target=worker,
            args=(i, base_url, pool, stop_event, result_queue, think_time),
            daemon=True,
        )
        workers.append(t)
        t.start()
        time.sleep(delay_between_threads)

    time.sleep(duration_seconds)
    stop_event.set()

    for t in workers:
        t.join(timeout=5)
    writer_thread.join(timeout=5)


def load_synthetic_manifest(csv_path: Path) -> list[dict]:
    resources = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            resources.append({
                "filename": row["resource"],
                "tier": "synthetic",
                "weight_override": int(row["weight"]),
            })

    return resources

def build_weighted_pool_from_synthetic(resources: list[dict]) -> list:
    pool = []
    for r in resources:
        weight = r["weight_override"]
        pool.extend([r]*weight)

    return pool

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Weighted load generator (HL report)")
    parser.add_argument("--base-url", type=str, default="http://127.0.0.1:8000")
    parser.add_argument("--manifest", type=Path, default=Path("server/static/manifest.csv"))
    parser.add_argument("--manifest-type", type=str, choices=["tier", "synthetic"], default="tier", 
                        help="'tier': weighted pool by dimensional category(real workload). "
                         "'synthetic': weighted pool by HL clustering(synthetic workload).")
    parser.add_argument("--threads", type=int, default=15)
    parser.add_argument("--duration", type=int, default=300)
    parser.add_argument("--ramp-up", type=int, default=15)
    parser.add_argument("--think-time", type=float, default=0)
    parser.add_argument("--output", type=Path, default=Path("data/raw/hl_report.csv"))

    args = parser.parse_args()

    print(f"Starting load test: {args.threads} threads, {args.duration}s duration, ramp-up {args.ramp_up}s")
    run_load_test(
        base_url=args.base_url,
        manifest_path=args.manifest,
        num_threads=args.threads,
        duration_seconds=args.duration,
        ramp_up_seconds=args.ramp_up,
        output_path=args.output,
        tier_weights=DEFAULT_TIER_WEIGHTS,
        think_time=args.think_time,
        manifest_type=args.manifest_type
    )

    print("Load test completed.")