"""
 * author Antonio Sirignano
 * created on 29-10-2026-10h-47m
 * github: https://github.com/antsiri
 * copyright 2026
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
    values: dict
    residues: np.ndarray = field(repr=False)

def linear_estimation(X: np.ndarray, Y: np.ndarray) -> tuple[dict, np.ndarray]:
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
    D, p = lilliefors(residues, dist='norm', pvalmethod='table')
    return {'KSL_D': D, 'KSL_p': p, 'normal_residuals': bool(p >= ALPHA)}

def trend_test(X: np.ndarray, Y: np.ndarray) -> dict:
    tau, p = stats.kendalltau(X, Y)
    return {'kendall_tau': tau, 'kendall_p': p, 'trend': bool(p < ALPHA)}

def theil_sen(X: np.ndarray, Y: np.ndarray) -> dict:
    ts = stats.theilslopes(Y, X, alpha=0.95)
    return {
        'ts_slope': ts.slope,
        'ts_intercept': ts.intercept,
        'ts_ic_inf': ts.low_slope,
        'ts_ic_sup': ts.high_slope,
        'slope_not_zero': bool(not (ts.low_slope <= 0 <= ts.high_slope))
    }

def analyze(sheet: str, df: pd.DataFrame, x: str, y:str) -> Analysis:
    X = df[x].to_numpy(dtype=float)
    Y = df[y].to_numpy(dtype=float)

    values = {'sheet': sheet, 'variable': y, 'x': x, 'n': len(Y), 'mean_y': Y.mean()}
    ols, residues = linear_estimation(X, Y)
    values |= ols
    values |= test_kls(residues)
    values |= trend_test(X, Y)
    if values['trend']:
        values |= theil_sen(X, Y)

    return Analysis(values=values, residues=residues)