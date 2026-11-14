"""
 * author Antonio Sirignano
 * created on 14-10-2026-17h-16m
 * github: https://github.com/antsiri
 * copyright 2026

Parser of the Mercury log format.
"""

from typing import List

from ffda.Logger.baselogger import BaseLogParser
from ffda.DataModels.datamodels import LogEntry


class MercuryLogParser(BaseLogParser):
    """
    Parser for lines formatted as ``<timestamp> <node> <category> <message...>``.
    """

    def parse(self) -> List[LogEntry]:
        """
        Read the log and build one LogEntry per valid line
        (lines with fewer than 4 fields are skipped).

        Returns:
            list[LogEntry]: parsed entries.
        """
        self.entries = []
        with open(self.log_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 4:
                    ts = float(parts[0])
                    node = parts[1]
                    cat = parts[2]
                    # The message may contain spaces: join the remaining fields
                    msg = " ".join(parts[3:])
                    self.entries.append(LogEntry(ts, node, cat, msg))
        return self.entries
