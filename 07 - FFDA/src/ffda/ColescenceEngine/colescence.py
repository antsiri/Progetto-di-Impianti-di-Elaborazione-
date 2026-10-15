"""
 * author Antonio Sirignano
 * created on 14-10-2026-17h-18m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import numpy as np

from typing import List, Dict

from ffda.DataModels.datamodels import LogEntry, CoalescedTuple

class CoalescenceEngine:

    @staticmethod
    def tuple_logs(entries: List[LogEntry], cwin: float) -> List[CoalescedTuple]:
        if not entries:
            return []

        sorted_entries = sorted(entries, key=lambda x: x.timestamp)
        tuples: List[CoalescedTuple] = []
        
        current_entries = [sorted_entries[0]]
        start_ts = sorted_entries[0].timestamp
        last_ts = start_ts
        tuple_id = 1

        for entry in sorted_entries[1:]:
            if entry.timestamp - last_ts <= cwin:
                current_entries.append(entry)
                last_ts = entry.timestamp
            else:
                tuples.append(CoalescedTuple(tuple_id, start_ts, last_ts, current_entries))
                tuple_id += 1
                current_entries = [entry]
                start_ts = entry.timestamp
                last_ts = entry.timestamp

        tuples.append(CoalescedTuple(tuple_id, start_ts, last_ts, current_entries))
        return tuples

    @staticmethod
    def calculate_inter_arrival_times(tuples: List[CoalescedTuple]) -> np.ndarray:
        if len(tuples) < 2:
            return np.array([])
        
        start_times = np.array([t.start_time for t in tuples])
        ttf = np.diff(start_times)  # Δt tra l'inizio di una tupla e la successiva
        return ttf[ttf > 0]

    def sensitivity_analysis(self, entries: List[LogEntry], cwin_values: List[float]) -> Dict[float, int]:
        results = {}
        for cwin in cwin_values:
            tuples = self.tuple_logs(entries, cwin)
            results[cwin] = len(tuples)
        return results