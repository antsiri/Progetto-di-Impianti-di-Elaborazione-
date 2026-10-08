"""
 * author Antonio Sirignano
 * created on 07-10-2026-21h-54m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import pandas as pd

from doe.Benchmark.benchmark_executor import BenchmarkExecutor

class DOERunner:
    def __init__(self, executor: BenchmarkExecutor):
        self.executor = executor
        self.intesities = [375, 1125]
        self.page_types = ['Low', 'Mid-Low', 'Mid', 'Mid-High', 'High']
        self.replications = 5

    def executre_full_factorial(self, duration_per_test: int = 40) -> pd.DataFrame:
        dataset = []
        total_test = (len(self.intesities) * len(self.page_types) * self.replications)
        current_test = 0

        print(f'[DOERunner] Starting Full Factorial Design ({total_test} total tests)...')

        for p_type in self.page_types:
            for intesity in self.intesities:
                for rep in range(1, self.replications + 1):
                    current_test += 1
                    print(f' Test {current_test}/{total_test}: Page={p_type}, Intesity={intesity}, Rep={rep}...')

                    rt = self.executor.runt_test(page_type=p_type,
                                                 intensity_req_per_min=intesity,
                                                 duration=duration_per_test,
                                                 )
                    dataset.append({
                        'Intensity': intesity,
                        'PageType': p_type,
                        'ResponseTime': rt
                    })

        df = pd.DataFrame(dataset)
        df.to_csv('measurements_doe.csv', index=False)
        print('[DOERunner] Experiments completed and saved in measurements_doe.csv')
        return df