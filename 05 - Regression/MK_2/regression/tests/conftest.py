"""
 * author Antonio Sirignano
 * created on 31-10-2026-10h-29m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import pytest

from regression.analysis import analyze
from regression.config import DEFAULT_DATA
from regression.data import load_data

@pytest.fixture(scope='session')
def dataset():
    if not DEFAULT_DATA.exists():
        pytest.skip(f'Data file not found: {DEFAULT_DATA}')
    return load_data(DEFAULT_DATA)

@pytest.fixture(scope='session')
def result(dataset):
    cache = {}

    def _get(sheet, y):
        if (sheet, y) not in cache:
            ds = dataset[sheet]
            cache[sheet, y] = analyze(sheet, ds.df, ds.x, y).values
        return cache[sheet, y]
    
    return _get