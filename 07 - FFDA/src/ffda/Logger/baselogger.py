"""
 * author Antonio Sirignano
 * created on 14-10-2026-17h-14m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import abc
import pandas as pd

from typing import List

from ffda.DataModels.datamodels import LogEntry

class BaseLogParser(abc.ABC):
    def __init__(self, log_path: str):
        self.log_path = log_path
        self.entries: List[LogEntry] = []

    @abc.abstractmethod
    def parse(self) -> List[LogEntry]:
        pass

    def filter_by_category(self, category: str) -> List[LogEntry]:
        return [e for e in self.entries if e.category == category]

    def filter_by_node(self, node: str) -> List[LogEntry]:
        return [e for e in self.entries if e.node == node]

    def get_statistics() -> pd.DataFrame:
        pass