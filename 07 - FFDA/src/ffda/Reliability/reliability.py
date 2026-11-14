"""
 * author Antonio Sirignano
 * created on 14-10-2026-17h-21m
 * github: https://github.com/antsiri
 * copyright 2026

Empirical reliability, model fitting and MTTF estimation.
"""
import numpy as np

from typing import Tuple
from scipy.optimize import curve_fit
from scipy.stats import kstest


class ReliabilityAnalyzer:
    """Compute the empirical reliability and fit theoretical regression models to it."""

    @staticmethod
    def compute_empirical_reliability(ttf_samples: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Empirical reliability ``R(t) = 1 - F_n(t)`` from the TTF samples.

        Args:
            ttf_samples (np.ndarray): times to failure.

        Returns:
            tuple[np.ndarray, np.ndarray]: sorted times and the corresponding R(t).
        """
        sorted_ttf = np.sort(ttf_samples)
        n = len(sorted_ttf)

        # Empirical CDF at the i-th sorted sample is i / n
        r_emp = 1.0 - (np.arange(1, n + 1) / n)
        return sorted_ttf, r_emp

    @staticmethod
    def exponential_model(t, a, b):
        """Exponential model: ``R(t) = a * exp(b * t)``."""
        return a * np.exp(b * t)

    @staticmethod
    def hyperexponential_model(t, a, b, d):
        """Hyperexponential model: ``R(t) = a * exp(b * t) + (1 - a) * exp(d * t)``."""
        return a * np.exp(b * t) + (1.0 - a) * np.exp(d * t)

    @staticmethod
    def weibull_model(t, a, b):
        """Weibull model: ``R(t) = exp(-b * t^a)``."""
        return np.exp(-b * (t ** a))

    def fit_model(self, model_type: str, t: np.ndarray, r_emp: np.ndarray):
        """
        Fit a reliability model to the empirical curve with non-linear least squares.

        Args:
            model_type (str): ``"exponential"``, ``"hyperexponential"`` or ``"weibull"``.
            t (np.ndarray): times.
            r_emp (np.ndarray): empirical reliability.

        Returns:
            dict: fitted ``params``, ``r_squared``, ``sse``, KS statistic and
            p-value, and ``predict_func`` (callable R(t) with fitted params).

        Raises:
            ValueError: on an unsupported model.
        """
        # Model function and initial guess of the parameters
        if model_type == "exponential":
            func = self.exponential_model
            p0 = [0.8, -0.0001]
        elif model_type == "hyperexponential":
            func = self.hyperexponential_model
            p0 = [0.4, -0.001, -0.0001]
            # Bounds: 0 <= a <= 1 (mixture weight), negative exponents
            bounds = ([0.0, -np.inf, -np.inf], [1.0, 0.0, 0.0])
            popt, pcov = curve_fit(func, t, r_emp, p0=p0, bounds=bounds, maxfev=10000)
        elif model_type == "weibull":
            func = self.weibull_model
            p0 = [0.5, 0.005]
        else:
            raise ValueError("Modello non supportato.")

        popt, pcov = curve_fit(func, t, r_emp, p0=p0, maxfev=10000)
        r_fit = func(t, *popt)

        # Goodness of fit: SSE and R² = 1 - SSE / SST
        sse = np.sum((r_emp - r_fit) ** 2)
        ss_tot = np.sum((r_emp - np.mean(r_emp)) ** 2)
        r_squared = 1 - (sse / ss_tot)

        # Two-sample KS test between empirical and fitted values
        ks_stat, p_value = kstest(r_emp, r_fit)

        return {
            "params": popt,
            "r_squared": r_squared,
            "sse": sse,
            "ks_stat": ks_stat,
            "p_value": p_value,
            "predict_func": lambda t_val: func(t_val, *popt)
        }

    @staticmethod
    def calculate_mttf(reliability_func, max_time: float = 300000) -> float:
        """
        Mean Time To Failure as the integral of R(t) over [0, max_time]
        (trapezoidal rule on 10000 points).

        Args:
            reliability_func (callable): R(t).
            max_time (float): upper integration limit (s).

        Returns:
            float: MTTF in seconds.
        """
        t_steps = np.linspace(0, max_time, 10000)
        r_vals = reliability_func(t_steps)
        mttf = np.trapezoid(r_vals, t_steps)
        return mttf
