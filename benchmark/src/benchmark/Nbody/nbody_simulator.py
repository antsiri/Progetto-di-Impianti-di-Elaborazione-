"""
 * author Antonio Sirignano
 * created on 10-10-2026-09h-12m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import time
import numpy as np
from numba import njit, prange

@njit(parallel=True, fastmath=True)
def _nbody_kernel(pos, vel, masses, G, dt, steps):
    n = pos.shape[0]
    eps = 1e-9

    for _ in range(steps):
        acc = np.zeros_like(pos)
        for i in prange(n):
            for j in range(n):
                if i != j:
                    dx = pos[j, 0] - pos[i, 0]
                    dy = pos[j, 1] - pos[i, 1]
                    dz = pos[j, 2] - pos[i, 2]

                    dist_sq = dx * dx + dy * dy + dz * dz + eps
                    inv_dist3 = dist_sq ** (-1.5)

                    f = G * masses[j, 0] * inv_dist3
                    acc[i, 0] += f * dx
                    acc[i, 1] += f * dy
                    acc[i, 2] += f * dz

        vel += acc * dt
        pos += vel * dt

class NbodySimulator:
    def __init__(self, n_bodies: int, steps: int = 5, dt: float = 0.01, G: float = 6.67430e-11, seed: int = 42):
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
        np.random.seed(self.seed)
        self.pos = np.random.randn(self.n_bodies, 3).astype(np.float64)
        self.vel = np.random.randn(self.n_bodies, 3).astype(np.float64)
        self.masses = np.random.randn(self.n_bodies, 1).astype(np.float64) + 1.0

    def _warmup_jit(self):
        pos_w = np.random.randn(100, 3).astype(np.float64)
        vel_w = np.random.randn(100, 3).astype(np.float64)
        masses_w = np.random.rand(100, 1).astype(np.float64) + 1.0
        _nbody_kernel(pos_w, vel_w, masses_w, self.G, self.dt, 1)

    def run_benchmark(self) -> float:
        self._reset_system()
        self._warmup_jit()

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
    if len(sys.argv) >= 3:
        steps_arg = int(sys.argv[1])
        bodies_arg = int(sys.argv[2])
        sim = NbodySimulator(n_bodies=bodies_arg,
                             steps=steps_arg
                             )
        print(f'{sim.run_benchmark():.4f}')            