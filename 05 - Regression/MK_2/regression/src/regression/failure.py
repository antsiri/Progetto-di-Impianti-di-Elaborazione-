"""
 * author Antonio Sirignano
 * created on 29-10-2026-23h-03m
 * github: https://github.com/antsiri
 * copyright 2026

Time-to-failure prediction from the Theil-Sen trend line.
"""

from .config import HEAP_LIMIT, SECONDS_YEAR


def failure_time(intercept: float, slope: float, limit: float = HEAP_LIMIT) -> float:
    """
    Time at which the line ``intercept + slope * t`` reaches ``limit``.

    Args:
        intercept (float): line intercept.
        slope (float): line slope.
        limit (float): resource capacity.

    Returns:
        float: time to failure (same unit as x), ``inf`` if the slope is not positive.
    """
    if slope <= 0:
        return float('inf')
    return (limit - intercept) / slope


def failure_prediction(values: dict, limit: float = HEAP_LIMIT) -> dict:
    """
    Time-to-failure estimate and its range from the slope confidence interval.

    Args:
        values (dict): analysis values containing the Theil-Sen results.
        limit (float): resource capacity.

    Returns:
        dict: slope/intercept info and failure times in seconds and years
        (nominal, minimum and maximum).
    """
    q = values['ts_intercept']
    t = failure_time(q, values['ts_slope'], limit)
    # Upper slope bound -> earliest failure; lower slope bound -> latest failure
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
