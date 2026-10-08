"""
 * author Antonio Sirignano
 * created on 08-10-2026-09h-50m
 * github: https://github.com/antsiri
 * copyright 2026
"""
import pandas as pd

from doe.Server.server_manager import ServerManager
from doe.Benchmark.benchmark_executor import BenchmarkExecutor
from doe.DOE.runner import DOERunner
from doe.DOE.analyzer import DOEAnalyzer

from pathlib import Path

CSV_PATH = Path('measurements_doe.csv')

if __name__ == '__main__':

    df_measured = None

    if CSV_PATH.exists():
        print('[MAIN] Measures are already present, jump the capture fase.')
        df_measured = pd.read_csv(CSV_PATH)
    else:
        server = ServerManager()
        server.setup_environment()
        server.start_server()

        try:
            executor = BenchmarkExecutor()
            runner = DOERunner(executor)
            df_measured = runner.executre_full_factorial(duration_per_test=60)

        finally:
            server.stop_server()

    analyzer = DOEAnalyzer(df_measured)
    analyzer.fit_linear_model()
    analyzer.compute_importance()
    analyzer.check_normality_shapiro()
    analyzer.check_significance_kruskal()
    analyzer.plot_diagnostics()