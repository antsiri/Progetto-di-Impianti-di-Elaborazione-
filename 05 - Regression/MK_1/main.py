"""
 * author Antonio Sirignano
 * created on 09-10-2026-16h-21m
 * github: https://github.com/antsiri
 * copyright 2026
"""

from regression.Orchestrator.monitoring_runner import MonitoringExperimentRunner

if __name__ == '__main__':
    output_file = 'measurement.csv'

    runner = MonitoringExperimentRunner(output_csv='measurement.csv', target_pid=None)

    runner.run(
        duration_seconds=3600,
        interval_seconds=1.0,
        x_col='TIME',
        y_col='RSS',
        capacity_limit_bytes=1073741824,
        force_remonitor=False,
    )
    