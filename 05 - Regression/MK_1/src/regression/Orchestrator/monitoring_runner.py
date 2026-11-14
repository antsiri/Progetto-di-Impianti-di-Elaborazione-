"""
 * author Antonio Sirignano
 * created on 09-10-2026-16h-12m
 * github: https://github.com/antsiri
 * copyright 2026

Orchestration of a monitoring session followed by the regression analysis.
"""
import os
import time

from regression.Monitor.monitor import SystemMonitor
from regression.Logger.logger import CSVLogger
from regression.Regression.analyzer import RegressionAnalyzer


class MonitoringExperimentRunner:
    """
    Ties together monitor, logger and regression analyzer.

    Attributes:
        output_csv (str): CSV where samples are stored.
        monitor (SystemMonitor): sampler of the target process.
        logger (CSVLogger): writer of the samples.
    """

    def __init__(self, output_csv: str = 'measurement.csv', target_pid: int = None):
        """
        Args:
            output_csv (str): CSV where samples are stored.
            target_pid (int | None): process to monitor (None = current process).
        """
        self.output_csv = output_csv
        self.monitor = SystemMonitor(pid=target_pid)
        self.logger = CSVLogger(output_csv)

    def execute_monitoring_session(self, duration_seconds: int = 30, interval_seconds: float = 1.0):
        """
        Sample the process periodically and log every sample to CSV.

        Args:
            duration_seconds (int): monitoring duration.
            interval_seconds (float): time between two samples.
        """
        print(f"[*] Staring monitoring on PID {self.monitor.process.pid} for {duration_seconds} seconds...")
        print(f"[*] Log will be saved in '{self.output_csv}'.")

        self.monitor.start()
        start_time = time.time()

        while (time.time() - start_time) < duration_seconds:
            sample = self.monitor.sample()
            self.logger.log_sample(sample)
            print(f"T={sample['TIME']:.1f}s | VmSize={sample['VmSize']/1024:.0f}KB | RSS={sample['RSS']/1024:.0f}KB")
            time.sleep(interval_seconds)

        print("\n[+] Monitoring completed successfully!")

    def analyze_results(self, x_col: str = "TIME", y_col: str = "VmSize", capacity_limit_bytes=None):
        """
        Run the regression analysis on the collected CSV and print the report.

        Args:
            x_col (str): independent variable column.
            y_col (str): dependent variable column.
            capacity_limit_bytes (float | None): resource limit for the
                failure prediction (default 1 GiB).
        """
        analyzer = RegressionAnalyzer(self.output_csv, x_col=x_col, y_col=y_col)
        report = analyzer.run_analysis(capacity_limit_bytes=capacity_limit_bytes if capacity_limit_bytes else 1073741824)
        print(report)

    def run(self, duration_seconds: int = 30, interval_seconds: float = 1.0,
            x_col: str = "TIME", y_col: str = "VmSize", capacity_limit_bytes: float = 1073741824,
            force_remonitor: bool = False,
            ):
        """
        Full workflow: monitoring (skipped if the CSV exists and
        ``force_remonitor`` is False) followed by the analysis.

        Args:
            duration_seconds (int): monitoring duration.
            interval_seconds (float): sampling interval.
            x_col (str): independent variable column.
            y_col (str): dependent variable column.
            capacity_limit_bytes (float): resource limit for the failure prediction.
            force_remonitor (bool): delete the existing CSV and monitor again.
        """

        file_exist = os.path.exists(self.output_csv)

        if file_exist and not force_remonitor:
            # Reuse previous measurements
            print(f"[i] The file '{self.output_csv}' is already present. Monitoring jumped.")
            print(f"[i] Direct execution of analysis...")
        else:
            # The logger appends: remove the old file to avoid mixing sessions
            if force_remonitor and file_exist:
                print(f"[!] Force monitoring active: deleting old file '{self.output_csv}'...")
                os.remove(self.output_csv)

            print(f"[*] File not found or force monitoring actived. Staring monitoring...")

            self.execute_monitoring_session(duration_seconds=duration_seconds,
                                            interval_seconds=interval_seconds,
                                            )

        self.analyze_results(x_col=x_col,
                             y_col=y_col,
                             capacity_limit_bytes=capacity_limit_bytes
                             )
