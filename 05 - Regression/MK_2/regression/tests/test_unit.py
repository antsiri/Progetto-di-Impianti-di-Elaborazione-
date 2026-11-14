"""
 * author Antonio Sirignano
 * created on 31-10-2026-10h-29m
 * github: https://github.com/antsiri
 * copyright 2026

Unit tests on synthetic data for analysis, cleaning and failure prediction.
"""

import numpy as np
import pandas as pd
import pytest

from regression.analysis import analyze
from regression.data import clean_sheet
from regression.failure import failure_prediction, failure_time


def perfect_line_test_has_a_trend_and_exact_slope():
    """A noiseless line y = 3 + 2x must give R² = 1 and exact Theil-Sen coefficients."""
    x = np.arange(100, dtype=float)
    df = pd.DataFrame({'t': x, 'y': 3.0 + 2.0 * x})
    r = analyze('test', df, 't', 'y').values
    assert r['R2'] == pytest.approx(1.0)
    assert r['trend']
    assert r['ts_slope'] == pytest.approx(2.0)
    assert r['ts_intercept'] == pytest.approx(3.0)
    assert r['slope_not_zero']


def pure_noise_test_has_no_trend():
    """Pure Gaussian noise must show no trend and normal residuals."""
    # Fixed seed for reproducibility
    rng = np.random.default_rng(0)
    df = pd.DataFrame({'t': np.arange(3000.0), 'y': rng.normal(size=3000)})
    r = analyze('test', df, 't', 'y').values
    assert not r['trend']
    # Without a trend Theil-Sen is not computed
    assert 'ts_slope' not in r
    assert r['normal_residuals']


def cleaning_test_removes_empty_columns_text_and_incomplete_lines():
    """Cleaning must drop empty columns, text columns and rows with NaN."""
    grezzo = pd.DataFrame({
        "TIME": [0, 120, 240, np.nan],
        "A": [1, 2, 3, 4],
        "empty": [np.nan] * 4,
        "note": [np.nan, "NO MEMORY DEPLETION!!!", np.nan, np.nan],
    })
    ds = clean_sheet("os2", grezzo)
    assert ds.x == "TIME"
    assert ds.ys == ["A"]
    assert len(ds.df) == 3


def uniform_cleaning_test_names_vmres():
    """VM resource sheets must get uniform column names."""
    ds = clean_sheet("VMres2", pd.DataFrame({"T (s)": [0, 60], "allocated heap": [1, 2]}))
    assert list(ds.df.columns) == ["T(s)", "Allocated Heap"]


def test_failure_time():
    """(limit - intercept) / slope, and infinity for a non-positive slope."""
    assert failure_time(intercept=100, slope=2, limit=300) == 100
    assert failure_time(intercept=100, slope=0, limit=300) == float("inf")


def test_failure_range_ordered():
    """The failure interval must satisfy T_min <= T_failure <= T_max."""
    r = {"sheet": "VMresX", "ts_intercept": 0.0, "ts_slope": 1.0, "ts_ic_inf": 0.5, "ts_ic_sup": 2.0}
    f = failure_prediction(r, limit=100)
    assert f["T_min_s"] == 50 and f["T_failure_s"] == 100 and f["T_max_s"] == 200
