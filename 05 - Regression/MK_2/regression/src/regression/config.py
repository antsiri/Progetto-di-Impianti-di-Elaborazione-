"""
 * author Antonio Sirignano
 * created on 29-10-2026-10h-26m
 * github: https://github.com/antsiri
 * copyright 2026

Global configuration constants and default paths.
"""

from pathlib import Path

# Significance level of all statistical tests
ALPHA = 0.05
# Heap capacity used for the failure prediction (1 GiB)
HEAP_LIMIT = 1024 ** 3
SECONDS_YEAR = 365 * 24 * 3600

# Paths: PROJECT_DIR = MK_2/regression, ROOT_DIR = MK_2
PROJECT_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = PROJECT_DIR.parent
DEFAULT_DATA = ROOT_DIR / 'data' / 'HomeWork_Regression.xls'
DEFAULT_OUTPUT = PROJECT_DIR / 'output'
