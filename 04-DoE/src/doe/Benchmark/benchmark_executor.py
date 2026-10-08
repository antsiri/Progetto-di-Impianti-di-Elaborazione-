"""
 * author Antonio Sirignano
 * created on 07-10-2026-18h-49m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import time
import requests
import numpy as np

class BenchmarkExecutor():
    def __init__(self, base_url='http://127.0.0.1:8080'):
        self.base_url = base_url

    def runt_test(self, page_type: str, intensity_req_per_min: int, duration: int = 60) -> float:
        target_url = f'{self.base_url}/{page_type}.html'
        interval = 60.0 / intensity_req_per_min
        response_times = []

        start_time = time.time()
        session = requests.Session()

        while (time.time() - start_time) < duration:
            t0 = time.perf_counter()
            try:
                res = session.get(target_url)
                t1 = time.perf_counter()
                if res.status_code == 200:
                    response_times.append((t1 - t0) * 1000)
            except Exception as e:
                print(f'Error: {e}')

            elapsed_step = time.perf_counter() - t0
            sleep_time = max(0, interval - elapsed_step)
            time.sleep(sleep_time)

        meean_rt = np.mean(response_times) if response_times else 0.0
        return round(meean_rt, 2)
        
