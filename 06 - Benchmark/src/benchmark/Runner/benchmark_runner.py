"""
 * author Antonio Sirignano
 * created on 10-10-2026-16h-18m
 * github: https://github.com/antsiri
 * copyright 2026

Data collection for the N-body benchmark.

Runs the simulator ``n_runs`` times for each problem size, each time in a
fresh Python process (independent runs), and saves the measured times in
``benchmark_<device>_<n_bodies>.txt``.
Usage: ``python3 benchmark_runner.py <laptop|desktop>``.
"""

import sys
import subprocess

from typing import List
from pathlib import Path


class BenchmarkRunner:
    """
    Executes and stores the benchmark runs of one device.

    Attributes:
        device_label (str): label used in the output file names.
        body_sizes (list[int]): problem sizes to test.
        n_runs (int): repetitions per size.
        steps (int): simulation steps per run.
    """

    def __init__(self, device_label: str, body_sizes: List[int] = None, n_runs: int = 31, steps: int = 5):
        """
        Args:
            device_label (str): device label (e.g. ``laptop``).
            body_sizes (list[int] | None): sizes (default [10000, 100000, 500000]).
            n_runs (int): repetitions per size.
            steps (int): simulation steps.
        """
        self.device_label = device_label
        self.body_sizes = body_sizes or [10000, 100000, 500000]
        self.n_runs = n_runs
        self.steps = steps

    def run_experiments(self, n_bodies: int) -> List[float]:
        """
        Run the simulator ``n_runs`` times for a given size.

        Args:
            n_bodies (int): number of bodies.

        Returns:
            list[float]: execution times in ms.
        """
        print(f'\n[RUNNER] Starting test: N = {n_bodies} ({self.n_runs} iterations on {self.device_label})...')
        times = []

        for i in range(1, self.n_runs + 1):
            # Fresh interpreter per run: no state/caches shared between runs
            cmd = [sys.executable, '/Users/antoniosirignano/Desktop/Progetto Impianti di Elaborazione/benchmark/src/benchmark/Nbody/nbody_simulator.py', str(self.steps), str(n_bodies)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            # The simulator prints only the elapsed time in ms
            t_ms = float(result.stdout.strip())
            times.append(t_ms)
            print(f'\t[Run {i:02d}/{self.n_runs}] Time: {t_ms:.2f} ms')

        return times

    def save_data(self, n_bodies: int, times: List[float]):
        """
        Save the times to ``benchmark_<device>_<n_bodies>.txt`` (one per line).

        Args:
            n_bodies (int): number of bodies.
            times (list[float]): measured times.
        """
        filename = f'benchmark_{self.device_label}_{n_bodies}.txt'
        with open(filename, 'w') as f:
            for t in times:
                f.write(f'{t}\n')

        print(f'[RUNNER] Data saved succefully in: {filename}')

    def execute(self):
        """Run and save the experiments for every configured size."""
        print(f'========================================')
        print(f'STARTING DATA COLLECTION ({self.device_label.upper()})')
        print(f'========================================')
        for n_bodies in self.body_sizes:
            times = self.run_experiments(n_bodies)
            self.save_data(n_bodies, times)
        print('[RUNNER] Data collection completed!')


if __name__ == "__main__":
    # The device label is mandatory
    if len(sys.argv) < 2:
        print("Using: python3 benchmark_runner.py <laptop|desktop>")
        sys.exit(1)

    runner = BenchmarkRunner(device_label=sys.argv[1])
    runner.execute()
