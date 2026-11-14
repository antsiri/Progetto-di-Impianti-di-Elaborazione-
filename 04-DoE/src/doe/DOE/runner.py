"""
 * author Antonio Sirignano
 * created on 07-10-2026-21h-54m
 * github: https://github.com/antsiri
 * copyright 2026

Execution of the full factorial experimental design.
"""

import pandas as pd

from doe.Benchmark.benchmark_executor import BenchmarkExecutor


class DOERunner:
    """
    Runs a full factorial design: 2 intensity levels x 5 page types,
    each combination replicated 5 times (50 tests in total).

    Attributes:
        executor (BenchmarkExecutor): object that performs the single tests.
        intesities (list[int]): request rates (requests/minute).
        page_types (list[str]): page size levels.
        replications (int): replications per combination.
    """

    def __init__(self, executor: BenchmarkExecutor):
        """
        Args:
            executor (BenchmarkExecutor): executor used for every test.
        """
        self.executor = executor
        # Factor levels of the experiment
        self.intesities = [375, 1125]
        self.page_types = ['Low', 'Mid-Low', 'Mid', 'Mid-High', 'High']
        self.replications = 5

    def executre_full_factorial(self, duration_per_test: int = 40) -> pd.DataFrame:
        """
        Run every (PageType, Intensity, replication) combination and save the
        results in ``measurements_doe.csv``.

        Args:
            duration_per_test (int): duration of each test in seconds.

        Returns:
            pandas.DataFrame: columns ``Intensity``, ``PageType``, ``ResponseTime``.
        """
        dataset = []
        total_test = (len(self.intesities) * len(self.page_types) * self.replications)
        current_test = 0

        print(f'[DOERunner] Starting Full Factorial Design ({total_test} total tests)...')

        # Nested loops over all factor levels and replications
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
