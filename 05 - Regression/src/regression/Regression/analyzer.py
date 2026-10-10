"""
 * author Antonio Sirignano
 * created on 09-10-2026-15h-19m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import pandas as pd
import numpy as np

from scipy.stats import kstest, kendalltau, norm, theilslopes

class RegressionAnalyzer:
    def __init__(self, csv_filepath: str, x_col: str, y_col: str):
        self.data = pd.read_csv(csv_filepath)
        self.x_col = x_col
        self.y_col = y_col
        self.x = self.data[x_col].values
        self.y = self.data[y_col].values

        self.ols_res = {}
        self.normality_res = {}
        self.kendall_res = {}
        self.theil_sen_res = {}
        self.failure_res = {}

    def fit_ols(self):
        p = np.polyfit(self.x, self.y, 1)
        slope, intercept = p[0], p[1]
        y_pred = slope * self.x + intercept
        residuals = self.y - y_pred

        ss_tot = np.sum((self.y - np.mean(self.y)) ** 2)
        ss_res = np.sum(residuals**2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        rmse = (np.sqrt(ss_res / (len(self.x) - 2)) if len(self.x) > 2 else 0)

        self.ols_res = {
            'slope': slope,
            'intercept': intercept,
            'r_squared': r_squared,
            'rmse': rmse,
            'residuals': residuals
        }

    def test_residual_normality(self):
        residuals = self.ols_res["residuals"]
        std_residuals = (
            (residuals - np.mean(residuals)) / np.std(residuals, ddof=1)
            if np.std(residuals) > 0
            else residuals
        )
        ks_stat, p_val = kstest(std_residuals, "norm")
        self.normality_res = {
            "stat": ks_stat,
            "p_value": p_val,
            "is_normal": p_val >= 0.01,
        }

    def test_kendall_trend(self):
        tau, p_val = kendalltau(self.x, self.y)
        self.kendall_res = {
            "tau": tau,
            "p_value": p_val,
            "has_trend": p_val < 0.05,
        }

    def fit_theil_sen(self):
        res = theilslopes(self.y, self.x, alpha=0.95)
        self.theil_sen_res = {
            "slope": res.slope,
            "intercept": res.intercept,
            "low_slope": res.low_slope,
            "high_slope": res.high_slope,
            "ci_includes_zero": (res.low_slope <= 0 <= res.high_slope),
        }

    def predict_failure(self, capacity_limit_bytes=1073741824):
        m = self.theil_sen_res["slope"]
        b = self.theil_sen_res["intercept"]
        low_m = self.theil_sen_res["low_slope"]
        high_m = self.theil_sen_res["high_slope"]

        if m <= 0 or high_m <= 0 or low_m <= 0:
            self.failure_res = None
            return

        t_fail_sec = (capacity_limit_bytes - b) / m
        t_fail_low = (capacity_limit_bytes - b) / high_m
        t_fail_high = (capacity_limit_bytes - b) / low_m

        delta_sec = abs(t_fail_high - t_fail_low) / 2.0
        sec_per_year = 365.25 * 24 * 3600

        self.failure_res = {
            "t_fail_sec": t_fail_sec,
            "delta_sec": delta_sec,
            "t_fail_years": t_fail_sec / sec_per_year,
            "delta_years": delta_sec / sec_per_year,
        }

    def run_analysis(self, capacity_limit_bytes=1073741824) -> str:
        self.fit_ols()
        self.test_residual_normality()
        self.test_kendall_trend()
        self.fit_theil_sen()
        self.predict_failure(capacity_limit_bytes)

        report = f"\n======================================================\n"
        report += (
            f" REAL MEASURMENT ANALYSIS: {self.y_col} vs {self.x_col}\n"
        )
        report += f"======================================================\n"
        report += f"1. OLS LINEAR ESTIMATION:\n"
        report += f"   - Equation: {self.y_col} = {self.ols_res['intercept']:.3f} + {self.ols_res['slope']:.6f} * {self.x_col}\n"
        report += f"   - R-squared (R²): {self.ols_res['r_squared']:.6f}\n"
        report += f"   - RMSE: {self.ols_res['rmse']:.3f}\n\n"

        report += f"2. RESIDUAL NOMRALITY TEST (KSL / Kolmogorov-Smirnov):\n"
        report += f"   - Statistic D: {self.normality_res['stat']:.6f}\n"
        report += f"   - p-value: {self.normality_res['p_value']:.4e}\n"
        report += f"   - Result: {'Normal' if self.normality_res['is_normal'] else 'NOT Normal (H0 Hypothesis Rejected)'}\n\n"

        report += f"3. MANN-KENDALL TEST (TREND):\n"
        report += f"   - Tau di Kendall (τ): {self.kendall_res['tau']:.6f}\n"
        report += f"   - p-value: {self.kendall_res['p_value']:.4e}\n"
        report += f"   - Presence of Trend: {'YES (Significance p < 0.05)' if self.kendall_res['has_trend'] else 'NO'}\n\n"

        report += f"4. THEIL-SEN ESTIMATOR:\n"
        report += f"   - Slope (m): {self.theil_sen_res['slope']:.6f}\n"
        report += f"   - Intercept (b): {self.theil_sen_res['intercept']:.3f}\n"
        report += f"   - CI 95%: [{self.theil_sen_res['low_slope']:.6f}, {self.theil_sen_res['high_slope']:.6f}]\n\n"

        if self.failure_res:
            report += f"5. FAILURE PREDICTION (memory Saturation at 1 GB):\n"
            report += f"   - Time to Failure: {self.failure_res['t_fail_sec']:.0f} ± {self.failure_res['delta_sec']:.0f} s\n"
            report += f"   - Time to Failure (Years): {self.failure_res['t_fail_years']:.2f} ± {self.failure_res['delta_years']:.2f} year\n"

        return report