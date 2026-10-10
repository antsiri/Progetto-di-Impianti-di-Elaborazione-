"""
 * author Antonio Sirignano
 * created on 10-10-2026-16h-18m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import sys
import subprocess

from typing import List
from pathlib import Path

class BenchmarkRunner:
    def __init__(self, device_label: str, body_sizes: List[int] = None, n_runs: int = 31, steps: int = 5):
        self.device_label = device_label
        self.body_sizes = body_sizes or [10000, 100000, 1000000]
        self.n_runs = n_runs
        self.steps = steps

    def run_experiments(self, n_bodies: int) -> List[float]:
        print(f'\n[RUNNER] Starting test: N = {n_bodies} ({self.n_runs} iterations on {self.device_label})...')
        times = []

        for i in range(1, self.n_runs + 1):
            cmd = [sys.executable, 'nbody_simulator.py', str(self.steps), str(n_bodies)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            t_ms = float(result.stdout.strip())
            times.append(t_ms)
            print(f'\t[Run {i:02d}/{self.n_runs}] Time: {t_ms:.2f} ms')

        return times

    def save_data(self, n_bodies: int, times: List[float]):
        filename = f'benchmark_{self.device_label}_{n_bodies}.txt'
        with open(filename, 'w') as f:
            for t in times:
                f.write(f'{t}\n')

        print(f'[RUNNER] Data saved succefully in: {filename}')

    def execute(self):
        print(f'========================================')
        print(f'STARTING DATA COLLECTION ({self.device_label.upper()})')
        print(f'========================================')
        for n_bodies in self.body_sizes:
            times = self.run_experiments(n_bodies)
            self.save_data(n_bodies, times)
        print('[RUNNER] Data collection completed!')

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Using: python3 benchmark_runner.py <laptop|desktop>")
        sys.exit(1)

    runner = BenchmarkRunner(device_label=sys.argv[1])
    runner.execute_all()