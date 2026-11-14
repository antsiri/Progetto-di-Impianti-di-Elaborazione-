"""
 * author Antonio Sirignano
 * created on 14-10-2026-17h-11m
 * github: https://github.com/antsiri
 * copyright 2026

Data models of the FFDA pipeline.
"""

from typing import List
from dataclasses import dataclass, field


@dataclass
class LogEntry:
    """
    Single parsed log line.

    Attributes:
        timestamp (float): epoch time in seconds.
        node (str): node that produced the message.
        category (str): error category.
        message (str): message text.
    """
    timestamp: float
    node: str
    category: str  # Ex: DEV, MEM, IO, NET, PRO, OTH for Mercury
    message: str


@dataclass
class CoalescedTuple:
    """
    Group of log entries close in time, assumed to describe one failure.

    Attributes:
        tuple_id (int): progressive identifier.
        start_time (float): timestamp of the first entry.
        end_time (float): timestamp of the last entry.
        entries (list[LogEntry]): entries of the tuple.
    """
    tuple_id: int
    start_time: float
    end_time: float
    entries: List[LogEntry] = field(default_factory=list)

    @property
    def duration(self) -> float:
        """Time span of the tuple in seconds."""
        return self.end_time - self.start_time

    @property
    def size(self) -> int:
        """Number of entries in the tuple."""
        return len(self.entries)
