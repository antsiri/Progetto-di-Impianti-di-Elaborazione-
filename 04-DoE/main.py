"""
 * author Antonio Sirignano
 * created on 08-10-2026-09h-50m
 * github: https://github.com/antsiri
 * copyright 2026

Entry point of the Design of Experiments (DoE) study.

If ``measurements_doe.csv`` already exists the measurement phase is skipped;
otherwise a local HTTP server is started and the full factorial experiment
(Intensity x PageType) is executed. The measures are then analysed with a
two-way ANOVA, importance analysis and non-parametric tests.
"""
import pandas as pd

from doe.Server.server_manager import ServerManager
from doe.Benchmark.benchmark_executor import BenchmarkExecutor
from doe.DOE.runner import DOERunner
from doe.DOE.analyzer import DOEAnalyzer

from pathlib import Path

# Cached measurements of a previous run
CSV_PATH = Path('measurements_doe.csv')

if __name__ == '__main__':

    df_measured = None

    if CSV_PATH.exists():
        # Reuse the existing measures (experiments are long)
        print('[MAIN] Measures are already present, jump the capture fase.')
        df_measured = pd.read_csv(CSV_PATH)
    else:
        # Generate the test pages and start the local web server
        server = ServerManager()
        server.setup_environment()
        server.start_server()

        try:
            # Run every factor combination with its replications
            executor = BenchmarkExecutor()
            runner = DOERunner(executor)
            df_measured = runner.executre_full_factorial(duration_per_test=60)

        finally:
            # Always shut the server down, even on errors
            server.stop_server()

    # Statistical analysis of the experiment
    analyzer = DOEAnalyzer(df_measured)
    analyzer.fit_linear_model()
    analyzer.compute_importance()
    analyzer.check_normality_shapiro()
    analyzer.check_significance_kruskal()
    analyzer.plot_diagnostics()
