"""
 * author Antonio Sirignano
 * created on 14-10-2026-17h-11m
 * github: https://github.com/antsiri
 * copyright 2026
"""

from typing import List
from dataclasses import dataclass, field

@dataclass
class LogEntry:
    timestamp: float
    node: str
    category: str  # Ex: DEV, MEM, IO, NET, PRO, OTH for Mercury
    message: str

@dataclass
class CoalescedTuple:
    tuple_id: int
    start_time: float
    end_time: float
    entries: List[LogEntry] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    @property
    def size(self) -> int:
        return len(self.entries)