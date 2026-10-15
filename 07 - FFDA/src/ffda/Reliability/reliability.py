"""
 * author Antonio Sirignano
 * created on 14-10-2026-17h-21m
 * github: https://github.com/antsiri
 * copyright 2026
"""
import numpy as np

from typing import Tuple
from scipy.optimize import curve_fit
from scipy.stats import kstest

class ReliabilityAnalyzer:
    """Calcola la Reliability empirica e mappa i modelli teorici di regressione[cite: 3, 4, 5]."""

    @staticmethod
    def compute_empirical_reliability(ttf_samples: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        sorted_ttf = np.sort(ttf_samples)
        n = len(sorted_ttf)
        
        r_emp = 1.0 - (np.arange(1, n + 1) / n)
        return sorted_ttf, r_emp

    @staticmethod
    def exponential_model(t, a, b):
        """f(x) = a * exp(b * x)[cite: 4]"""
        return a * np.exp(b * t)

    @staticmethod
    def hyperexponential_model(t, a, b, d):
        return a * np.exp(b * t) + (1.0 - a) * np.exp(d * t)

    @staticmethod
    def weibull_model(t, a, b):
        """f(x) = e^(-b * t^a)[cite: 5]"""
        return np.exp(-b * (t ** a))

    def fit_model(self, model_type: str, t: np.ndarray, r_emp: np.ndarray):
        if model_type == "exponential":
            func = self.exponential_model
            p0 = [0.8, -0.0001]
        elif model_type == "hyperexponential":
            func = self.hyperexponential_model
            p0 = [0.4, -0.001, -0.0001]
            bounds = ([0.0, -np.inf, -np.inf], [1.0, 0.0, 0.0])
            popt, pcov = curve_fit(func, t, r_emp, p0=p0, bounds=bounds, maxfev=10000)
        elif model_type == "weibull":
            func = self.weibull_model
            p0 = [0.5, 0.005]
        else:
            raise ValueError("Modello non supportato.")

        popt, pcov = curve_fit(func, t, r_emp, p0=p0, maxfev=10000)
        r_fit = func(t, *popt)

        sse = np.sum((r_emp - r_fit) ** 2)
        ss_tot = np.sum((r_emp - np.mean(r_emp)) ** 2)
        r_squared = 1 - (sse / ss_tot)

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
        t_steps = np.linspace(0, max_time, 10000)
        r_vals = reliability_func(t_steps)
        mttf = np.trapezoid(r_vals, t_steps)
        return mttf