"""
 * author Antonio Sirignano
 * created on 14-10-2026-17h-25m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import matplotlib.pyplot as plt
import numpy as np

from typing import Dict

class ReliabilityVisualizer:
    @staticmethod
    def plot_sensitivity(cwin_dict: Dict[float, int], chosen_cwin: float = None, filename: str = "cwin_sensitivity.png"):
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
        plt.figure(figsize=(8, 5))
        plt.plot(t, r_emp, 'k.', label="Empirical R(t)")
        
        t_line = np.linspace(0, np.max(t), 1000)
        r_fit = fit_dict["predict_func"](t_line)
        plt.plot(t_line, r_fit, 'b-', label=f"Fit (R²={fit_dict['r_squared']:.4f})")

        plt.title(title)
        plt.xlabel("t [s]")
        plt.ylabel("Reliability R(t)")
        plt.grid(True)
        plt.savefig("plot_reliability_fit", bbox_inches='tight', dpi=300)
        plt.close()