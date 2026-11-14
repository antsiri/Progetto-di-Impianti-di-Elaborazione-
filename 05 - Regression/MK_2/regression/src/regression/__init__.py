"""
Regression package (MK_2): software-aging analysis of the homework dataset.

Public API re-exported from the sub-modules.
"""

from .analysis import Analysis, analyze
from .data import Dataset, load_data
from .failure import failure_prediction, failure_time

__all__ = ['Analysis', 'Dataset', 'analyze', 'load_data', 'failure_prediction', 'failure_time']
