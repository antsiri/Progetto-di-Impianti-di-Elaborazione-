"""
 * author Antonio Sirignano
 * created on 09-10-2026-09h-58m
 * github: https://github.com/antsiri
 * copyright 2026

Process memory and I/O monitor based on psutil.
"""

import os
import pandas as pd
import numpy as np
import psutil
import time


class SystemMonitor:
    """
    Samples memory usage (VmSize, VmData, RSS) and I/O rate of a process.

    Attributes:
        process (psutil.Process): monitored process.
        start_time (float | None): time at which monitoring started.
    """

    def __init__(self, pid: int = None):
        """
        Args:
            pid (int | None): PID to monitor; None means the current process.
        """
        if pid is None:
            self.process = psutil.Process(os.getpid())
        else:
            self.process = psutil.Process(pid=pid)

        self.start_time = None
        self._last_io = None

    def start(self):
        """Store the start time and the initial I/O counters (if available)."""
        self.start_time = time.time()
        try:
            self._last_io = self.process.io_counters()
        except (AttributeError, psutil.AccessDenied):
            # io_counters() is not available on every OS (e.g. macOS)
            self._last_io = None

    def sample(self) -> dict:
        """
        Take one sample of the monitored process.

        Returns:
            dict: ``TIME`` (s since start), ``VmSize``, ``VmData``, ``RSS``
            (bytes) and ``byte_r_sec`` / ``byte_w_sec`` (I/O rate).
        """
        current_time = time.time()
        elapsed_time = current_time - self.start_time

        # Virtual memory size and resident set size
        mem_info = self.process.memory_info()
        vmsize = getattr(
            mem_info, 'vms', 0
        )
        rss = getattr(
            mem_info, 'rss', 0
        )

        # 'data' exists only on Linux; elsewhere it is approximated as VMS - RSS
        vmdata = getattr(mem_info, 'data', max(0, vmsize - rss))

        byte_r_sec = 0
        byte_w_sec = 0
        try:
            current_io = self.process.io_counters()
            if self._last_io:
                # Average rate since the start of monitoring
                dt = (
                    elapsed_time if elapsed_time > 0 else 1
                )
                byte_r_sec = (
                    current_io.read_bytes - self._last_io.read_bytes
                ) / dt
                byte_w_sec = (
                    current_io.write_bytes - self._last_io.write_bytes
                ) / dt
        except (AttributeError, psutil.AccessDenied):
            pass

        return {
            'TIME': elapsed_time,
            'VmSize': vmsize,
            'VmData': vmdata,
            'RSS': rss,
            'byte_r_sec': byte_r_sec,
            'byte_w_sec': byte_w_sec
        }
