"""
 * author Antonio Sirignano
 * created on 09-10-2026-16h-12m
 * github: https://github.com/antsiri
 * copyright 2026
"""
import os
import time

from regression.Monitor.monitor import SystemMonitor
from regression.Logger.logger import CSVLogger
from regression.Regression.analyzer import RegressionAnalyzer

class MonitoringExperimentRunner:

    def __init__(self, output_csv: str = 'measurement.csv', target_pid: int = None):
        self.output_csv = output_csv
        self.monitor = SystemMonitor(pid=target_pid)
        self.logger = CSVLogger(output_csv)

    def execute_monitoring_session(self, duration_seconds: int = 30, interval_seconds: float = 1.0):
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
        analyzer = RegressionAnalyzer(self.output_csv, x_col=x_col, y_col=y_col)
        report = analyzer.run_analysis(capacity_limit_bytes=capacity_limit_bytes if capacity_limit_bytes else 1073741824)
        print(report)

    def run(self, duration_seconds: int = 30, interval_seconds: float = 1.0,
            x_col: str = "TIME", y_col: str = "VmSize", capacity_limit_bytes: float = 1073741824,
            force_remonitor: bool = False,
            ):

        file_exist = os.path.exists(self.output_csv)

        if file_exist and not force_remonitor:
            print(f"[i] The file '{self.output_csv}' is already present. Monitoring jumped.")
            print(f"[i] Direct execution of analysis...")
        else:
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