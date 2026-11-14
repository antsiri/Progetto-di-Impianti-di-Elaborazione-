"""
 * author Antonio Sirignano
 * created on 10-10-2026-09h-12m
 * github: https://github.com/antsiri
 * copyright 2026

N-body gravitational simulation used as CPU benchmark.

The O(n^2) force computation is compiled with Numba (parallel, fastmath).
When executed as a script it prints the execution time in ms:
``python nbody_simulator.py <steps> <n_bodies>``.
"""

import time
import numpy as np
from numba import njit, prange


@njit(parallel=True, fastmath=True)
def _nbody_kernel(pos, vel, masses, G, dt, steps):
    """
    Advance the system by ``steps`` time steps (in place).

    For every body the gravitational acceleration due to all the other
    bodies is computed (direct O(n^2) sum), then velocities and positions
    are updated with an explicit Euler step.

    Args:
        pos (np.ndarray): positions ``(n, 3)``, updated in place.
        vel (np.ndarray): velocities ``(n, 3)``, updated in place.
        masses (np.ndarray): masses ``(n, 1)``.
        G (float): gravitational constant.
        dt (float): time step.
        steps (int): number of steps.
    """
    n = pos.shape[0]
    # Softening term: avoids division by zero when two bodies coincide
    eps = 1e-9

    for _ in range(steps):
        acc = np.zeros_like(pos)
        # Outer loop parallelised across threads by Numba (prange)
        for i in prange(n):
            for j in range(n):
                if i != j:
                    # Distance vector from body i to body j
                    dx = pos[j, 0] - pos[i, 0]
                    dy = pos[j, 1] - pos[i, 1]
                    dz = pos[j, 2] - pos[i, 2]

                    # 1 / |r|^3 (softened)
                    dist_sq = dx * dx + dy * dy + dz * dz + eps
                    inv_dist3 = dist_sq ** (-1.5)

                    # a_i += G * m_j * r_ij / |r_ij|^3
                    f = G * masses[j, 0] * inv_dist3
                    acc[i, 0] += f * dx
                    acc[i, 1] += f * dy
                    acc[i, 2] += f * dz

        # Explicit Euler integration
        vel += acc * dt
        pos += vel * dt


class NbodySimulator:
    """
    Wrapper that initialises a random system and times the kernel.

    Attributes:
        n_bodies (int): number of bodies.
        steps (int): simulation steps per benchmark.
        dt (float): time step.
        G (float): gravitational constant.
        seed (int): RNG seed (same initial state on every run).
    """

    def __init__(self, n_bodies: int, steps: int = 5, dt: float = 0.01, G: float = 6.67430e-11, seed: int = 42):
        """
        Args:
            n_bodies (int): number of bodies.
            steps (int): simulation steps.
            dt (float): time step.
            G (float): gravitational constant.
            seed (int): RNG seed.
        """
        self.n_bodies = n_bodies
        self.steps = steps
        self.dt = dt
        self.G = G
        self.seed = seed
        self.pos = None
        self.vel = None
        self.masses = None
        self._reset_system()

    def _reset_system(self):
        """Generate reproducible random positions, velocities and masses."""
        np.random.seed(self.seed)
        self.pos = np.random.randn(self.n_bodies, 3).astype(np.float64)
        self.vel = np.random.randn(self.n_bodies, 3).astype(np.float64)
        self.masses = np.random.randn(self.n_bodies, 1).astype(np.float64) + 1.0

    def _warmup_jit(self):
        """
        Call the kernel once on a tiny system so that the Numba JIT
        compilation time is excluded from the measurement.
        """
        pos_w = np.random.randn(100, 3).astype(np.float64)
        vel_w = np.random.randn(100, 3).astype(np.float64)
        masses_w = np.random.rand(100, 1).astype(np.float64) + 1.0
        _nbody_kernel(pos_w, vel_w, masses_w, self.G, self.dt, 1)

    def run_benchmark(self) -> float:
        """
        Run the simulation and measure its wall-clock time.

        Returns:
            float: execution time in milliseconds.
        """
        self._reset_system()
        self._warmup_jit()

        # Only the compiled kernel execution is timed
        start_time = time.perf_counter()
        _nbody_kernel(pos=self.pos,
                        vel=self.vel,
                        masses=self.masses,
                        G=self.G,
                        dt=self.dt,
                        steps=self.steps,
                        )
        end_time = time.perf_counter()

        return (end_time - start_time) * 1000.0


if __name__ == '__main__':
    import sys
    # Usage: nbody_simulator.py <steps> <n_bodies>; output parsed by benchmark_runner.py
    if len(sys.argv) >= 3:
        steps_arg = int(sys.argv[1])
        bodies_arg = int(sys.argv[2])
        sim = NbodySimulator(n_bodies=bodies_arg,
                             steps=steps_arg
                             )
        print(f'{sim.run_benchmark():.4f}')
