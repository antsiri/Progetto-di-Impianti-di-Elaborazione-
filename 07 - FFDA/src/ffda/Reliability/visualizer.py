"""
 * author Antonio Sirignano
 * created on 14-10-2026-17h-25m
 * github: https://github.com/antsiri
 * copyright 2026

Plots of the FFDA analysis.
"""

import matplotlib.pyplot as plt
import numpy as np

from typing import Dict


class ReliabilityVisualizer:
    """Static plotting helpers for CWIN sensitivity and reliability fit."""

    @staticmethod
    def plot_sensitivity(cwin_dict: Dict[float, int], chosen_cwin: float = None, filename: str = "cwin_sensitivity.png"):
        """
        Plot the number of tuples as a function of the coalescence window.

        Args:
            cwin_dict (dict[float, int]): CWIN -> number of tuples.
            chosen_cwin (float | None): selected CWIN, drawn as a vertical line.
            filename (str): intended output file name.
        """
        plt.figure(figsize=(8, 5))
        plt.plot(list(cwin_dict.keys()), list(cwin_dict.values()), 'b*-')
        if chosen_cwin:
            plt.axvline(x=chosen_cwin, color='r', linestyle='--', label=f'CWIN Scelta ({chosen_cwin}s)')
        plt.title("Sensitivity Analysis - Coalescence Window (CWIN)")
        plt.xlabel("CWIN [s]")
        plt.ylabel("Numero di Tuple")
        plt.grid(True)
        plt.legend()
        plt.savefig("plot_sensitivity.png", bbox_inches='tight', dpi=300)
        plt.close()

    @staticmethod
    def plot_reliability_fit(t: np.ndarray, r_emp: np.ndarray, fit_dict: dict, title: str = "Fit Plot", filename: str = "reliability_fit.png"):
        """
        Plot the empirical reliability against the fitted model.

        Args:
            t (np.ndarray): times.
            r_emp (np.ndarray): empirical reliability.
            fit_dict (dict): output of ``ReliabilityAnalyzer.fit_model``.
            title (str): plot title.
            filename (str): intended output file name.
        """
        plt.figure(figsize=(8, 5))
        plt.plot(t, r_emp, 'k.', label="Empirical R(t)")

        # Fitted curve evaluated on a dense, regular grid
        t_line = np.linspace(0, np.max(t), 1000)
        r_fit = fit_dict["predict_func"](t_line)
        plt.plot(t_line, r_fit, 'b-', label=f"Fit (R²={fit_dict['r_squared']:.4f})")

        plt.title(title)
        plt.xlabel("t [s]")
        plt.ylabel("Reliability R(t)")
        plt.grid(True)
        plt.savefig("plot_reliability_fit", bbox_inches='tight', dpi=300)
        plt.close()
