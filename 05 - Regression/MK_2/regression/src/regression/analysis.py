"""
 * author Antonio Sirignano
 * created on 29-10-2026-10h-47m
 * github: https://github.com/antsiri
 * copyright 2026

Statistical analysis of a (time, resource) series.

OLS linear estimation, Lilliefors (KSL) normality test on residuals,
Mann-Kendall trend test (Kendall tau) and, when a trend exists, the
Theil-Sen robust slope estimator.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm

from scipy import stats
from statsmodels.stats.diagnostic import lilliefors

from dataclasses import dataclass, field

from .config import ALPHA


@dataclass
class Analysis:
    """
    Result of :func:`analyze`.

    Attributes:
        values (dict): every computed indicator (flat dictionary).
        residues (np.ndarray): OLS residuals (hidden from ``repr``).
    """
    values: dict
    residues: np.ndarray = field(repr=False)


def linear_estimation(X: np.ndarray, Y: np.ndarray) -> tuple[dict, np.ndarray]:
    """
    Ordinary least squares fit ``Y = intercept + slope * X``.

    Args:
        X (np.ndarray): independent variable.
        Y (np.ndarray): dependent variable.

    Returns:
        tuple[dict, np.ndarray]: coefficients, standard errors, p-values,
        R², adjusted R², RMSE, F statistic, and the residuals.
    """
    # add_constant adds the intercept column to the design matrix
    model = sm.OLS(Y, sm.add_constant(X)).fit()
    values = {
        'ols_intercept': model.params[0],
        'ols_slope': model.params[1],
        'ols_std_err_intercept': model.bse[0],
        'ols_std_err_solpe': model.bse[1],
        'ols_p_slope': model.pvalues[1],
        'R2': model.rsquared,
        'Correct_R2': model.rsquared_adj,
        'RMSE': np.sqrt(model.mse_resid),
        'F': model.fvalue,
        'p_F': model.f_pvalue,
    }
    return values, np.asarray(model.resid)


def test_kls(residues: np.ndarray) -> dict:
    """
    Lilliefors (Kolmogorov-Smirnov with estimated parameters) normality test.

    Args:
        residues (np.ndarray): OLS residuals.

    Returns:
        dict: ``KSL_D``, ``KSL_p`` and ``normal_residuals`` (p >= ALPHA).
    """
    D, p = lilliefors(residues, dist='norm', pvalmethod='table')
    return {'KSL_D': D, 'KSL_p': p, 'normal_residuals': bool(p >= ALPHA)}


def trend_test(X: np.ndarray, Y: np.ndarray) -> dict:
    """
    Mann-Kendall trend test via Kendall's tau.

    Args:
        X (np.ndarray): time.
        Y (np.ndarray): resource values.

    Returns:
        dict: ``kendall_tau``, ``kendall_p`` and ``trend`` (p < ALPHA).
    """
    tau, p = stats.kendalltau(X, Y)
    return {'kendall_tau': tau, 'kendall_p': p, 'trend': bool(p < ALPHA)}


def theil_sen(X: np.ndarray, Y: np.ndarray) -> dict:
    """
    Theil-Sen robust estimation of slope and intercept with 95% CI.

    Args:
        X (np.ndarray): time.
        Y (np.ndarray): resource values.

    Returns:
        dict: slope, intercept, CI bounds and ``slope_not_zero``
        (True if 0 is outside the confidence interval).
    """
    ts = stats.theilslopes(Y, X, alpha=0.95)
    return {
        'ts_slope': ts.slope,
        'ts_intercept': ts.intercept,
        'ts_ic_inf': ts.low_slope,
        'ts_ic_sup': ts.high_slope,
        'slope_not_zero': bool(not (ts.low_slope <= 0 <= ts.high_slope))
    }


def analyze(sheet: str, df: pd.DataFrame, x: str, y:str) -> Analysis:
    """
    Run the complete analysis of column ``y`` against column ``x``.

    Args:
        sheet (str): name of the source sheet (stored in the results).
        df (pandas.DataFrame): cleaned data.
        x (str): independent variable column (time).
        y (str): dependent variable column (resource).

    Returns:
        Analysis: all indicators and the OLS residuals.
    """
    X = df[x].to_numpy(dtype=float)
    Y = df[y].to_numpy(dtype=float)

    values = {'sheet': sheet, 'variable': y, 'x': x, 'n': len(Y), 'mean_y': Y.mean()}
    ols, residues = linear_estimation(X, Y)
    # Merge the results of every step into a single dictionary (|= is dict update)
    values |= ols
    values |= test_kls(residues)
    values |= trend_test(X, Y)
    # Theil-Sen is computed only if a significant trend exists
    if values['trend']:
        values |= theil_sen(X, Y)

    return Analysis(values=values, residues=residues)
