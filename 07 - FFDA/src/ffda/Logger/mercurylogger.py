"""
 * author Antonio Sirignano
 * created on 14-10-2026-17h-16m
 * github: https://github.com/antsiri
 * copyright 2026
"""

from typing import List

from ffda.Logger.baselogger import BaseLogParser
from ffda.DataModels.datamodels import LogEntry

class MercuryLogParser(BaseLogParser):
    def parse(self) -> List[LogEntry]:
        self.entries = []
        with open(self.log_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 4:
                    ts = float(parts[0])
                    node = parts[1]
                    cat = parts[2]
                    msg = " ".join(parts[3:])
                    self.entries.append(LogEntry(ts, node, cat, msg))
        return self.entries