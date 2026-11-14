"""
 * author Antonio Sirignano
 * created on 14-10-2026-17h-18m
 * github: https://github.com/antsiri
 * copyright 2026

Temporal coalescence (tupling) of log entries.
"""

import numpy as np

from typing import List, Dict

from ffda.DataModels.datamodels import LogEntry, CoalescedTuple


class CoalescenceEngine:
    """
    Groups log entries that are close in time into tuples (one tuple ~ one
    failure) and derives the times between failures.
    """

    @staticmethod
    def tuple_logs(entries: List[LogEntry], cwin: float) -> List[CoalescedTuple]:
        """
        Tupling algorithm with a coalescence window.

        An entry joins the current tuple if it occurs within ``cwin`` seconds
        of the *last* entry of that tuple; otherwise a new tuple is opened.

        Args:
            entries (list[LogEntry]): log entries (any order).
            cwin (float): coalescence window in seconds.

        Returns:
            list[CoalescedTuple]: tuples in chronological order.
        """
        if not entries:
            return []

        sorted_entries = sorted(entries, key=lambda x: x.timestamp)
        tuples: List[CoalescedTuple] = []

        # The first entry opens the first tuple
        current_entries = [sorted_entries[0]]
        start_ts = sorted_entries[0].timestamp
        last_ts = start_ts
        tuple_id = 1

        for entry in sorted_entries[1:]:
            if entry.timestamp - last_ts <= cwin:
                # Close enough to the previous entry: same tuple
                current_entries.append(entry)
                last_ts = entry.timestamp
            else:
                # Gap larger than CWIN: close the current tuple and open a new one
                tuples.append(CoalescedTuple(tuple_id, start_ts, last_ts, current_entries))
                tuple_id += 1
                current_entries = [entry]
                start_ts = entry.timestamp
                last_ts = entry.timestamp

        # Close the last open tuple
        tuples.append(CoalescedTuple(tuple_id, start_ts, last_ts, current_entries))
        return tuples

    @staticmethod
    def calculate_inter_arrival_times(tuples: List[CoalescedTuple]) -> np.ndarray:
        """
        Times to failure: differences between start times of consecutive tuples.

        Args:
            tuples (list[CoalescedTuple]): tuples in chronological order.

        Returns:
            np.ndarray: strictly positive inter-arrival times (empty if < 2 tuples).
        """
        if len(tuples) < 2:
            return np.array([])

        start_times = np.array([t.start_time for t in tuples])
        ttf = np.diff(start_times)  # Δt between the start of a tuple and the next one
        return ttf[ttf > 0]

    def sensitivity_analysis(self, entries: List[LogEntry], cwin_values: List[float]) -> Dict[float, int]:
        """
        Number of tuples obtained for each candidate CWIN value.

        Args:
            entries (list[LogEntry]): log entries.
            cwin_values (list[float]): windows to try.

        Returns:
            dict[float, int]: CWIN -> number of tuples.
        """
        results = {}
        for cwin in cwin_values:
            tuples = self.tuple_logs(entries, cwin)
            results[cwin] = len(tuples)
        return results
