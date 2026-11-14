"""
 * author Antonio Sirignano
 * created on 09-10-2026-16h-21m
 * github: https://github.com/antsiri
 * copyright 2026

Entry point of the software-aging regression experiment (MK_1).

Monitors the memory of a process for one hour (or reuses an existing
``measurement.csv``), then fits a regression of RSS over time and predicts
when the 1 GB memory limit would be reached.
"""

from regression.Orchestrator.monitoring_runner import MonitoringExperimentRunner

if __name__ == '__main__':
    output_file = 'measurement.csv'

    # target_pid=None -> monitor the current Python process
    runner = MonitoringExperimentRunner(output_csv='measurement.csv', target_pid=None)

    # 1 h of sampling at 1 Hz; regression of RSS vs TIME with a 1 GiB capacity limit
    runner.run(
        duration_seconds=3600,
        interval_seconds=1.0,
        x_col='TIME',
        y_col='RSS',
        capacity_limit_bytes=1073741824,
        force_remonitor=False,
    )

