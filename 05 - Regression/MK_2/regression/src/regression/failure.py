"""
 * author Antonio Sirignano
 * created on 29-10-2026-23h-03m
 * github: https://github.com/antsiri
 * copyright 2026
"""

from .config import HEAP_LIMIT, SECONDS_YEAR

def failure_time(intercept: float, slope: float, limit: float = HEAP_LIMIT) -> float:
    if slope <= 0:
        return float('inf')
    return (limit - intercept) / slope

def failure_prediction(values: dict, limit: float = HEAP_LIMIT) -> dict:
    q = values['ts_intercept']
    t = failure_time(q, values['ts_slope'], limit)
    t_min = failure_time(q, values['ts_ic_sup'], limit)
    t_max = failure_time(q, values['ts_ic_inf'], limit)
    return {
        'sheet': values['sheet'],
        'slope': values['ts_slope'],
        'intercept': q,
        'ic_inf_slope': values['ts_ic_inf'],
        'ic_sup_slope': values['ts_ic_sup'],
        'T_failure_s': t,
        'T_min_s': t_min,
        'T_max_s': t_max,
        'T_failure_years': t / SECONDS_YEAR,
        'T_min_years': t_min / SECONDS_YEAR,
        'T_max_years': t_max / SECONDS_YEAR,
    }
