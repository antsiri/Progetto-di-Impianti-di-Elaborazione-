"""
 * author Antonio Sirignano
 * created on 14-10-2026-17h-14m
 * github: https://github.com/antsiri
 * copyright 2026

Abstract base class of the log parsers.
"""

import abc
import pandas as pd

from typing import List

from ffda.DataModels.datamodels import LogEntry


class BaseLogParser(abc.ABC):
    """
    Common interface for log parsers: subclasses implement :meth:`parse`
    for a specific log format.

    Attributes:
        log_path (str): log file to parse.
        entries (list[LogEntry]): entries produced by the last :meth:`parse`.
    """

    def __init__(self, log_path: str):
        """
        Args:
            log_path (str): log file to parse.
        """
        self.log_path = log_path
        self.entries: List[LogEntry] = []

    @abc.abstractmethod
    def parse(self) -> List[LogEntry]:
        """Parse the log file and return (and store) the list of entries."""
        pass

    def filter_by_category(self, category: str) -> List[LogEntry]:
        """Return the parsed entries of the given category."""
        return [e for e in self.entries if e.category == category]

    def filter_by_node(self, node: str) -> List[LogEntry]:
        """Return the parsed entries produced by the given node."""
        return [e for e in self.entries if e.node == node]

    def get_statistics() -> pd.DataFrame:
        """Placeholder for summary statistics of the entries (not implemented)."""
        pass
