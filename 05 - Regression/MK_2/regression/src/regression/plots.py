"""
 * author Antonio Sirignano
 * created on 30-10-2026-12h-01m
 * github: https://github.com/antsiri
 * copyright 2026

Diagnostic plots of a regression analysis.
"""

from pathlib import Path

import matplotlib
# Non-interactive backend: figures are only saved to file
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.axes._axes as axes
import matplotlib.figure as figure
import numpy as np
import pandas as pd

from scipy import stats

from .analysis import Analysis


def pair_plot(df: pd.DataFrame, analysis: Analysis, folder: Path) -> Path:
    """
    Save a 3-panel figure: data with OLS (and Theil-Sen) lines, residual
    histogram with fitted normal density, and normal QQ-plot of residuals.

    Args:
        df (pandas.DataFrame): data of the sheet.
        analysis (Analysis): result of :func:`regression.analysis.analyze`.
        folder (Path): destination folder.

    Returns:
        Path: path of the saved PNG (``<sheet>_<variable>.png``).
    """
    r = analysis.values
    residues = analysis.residues

    x = r['x']
    y = r['variable']

    X = df[x].to_numpy(dtype=float)
    Y = df[y].to_numpy(dtype=float)

    fig, ax = plt.subplots(1, 3, figsize=(16, 4.5))

    # 1. Scatter of the data with the fitted lines
    ax[0].scatter(X, Y, s=4, color='black')
    xs = np.array([X.min(), X.max()])
    ax[0].plot(xs, r['ols_intercept'] + r['ols_slope'] * xs, color='red', label=f'OLS (R2 = {r['R2']:.4f})')
    if r['trend']:
        ax[0].plot(xs, r['ts_intercept'] + r['ts_slope'] * xs, color='tab:blue', linestyle='--', label='Theil-Sen')
    ax[0].set(title=f'{y} compered to {x}', xlabel=x, ylabel=y)
    ax[0].legend(fontsize=8)

    # 2. Histogram of residuals vs normal PDF with the same mean / std
    ax[1].hist(residues, bins=40, density=True, color='#9fb59f', edgecolor='gray')
    grid = np.linspace(residues.min(), residues.max(), 300)
    ax[1].plot(grid, stats.norm.pdf(grid, residues.mean(), residues.std(ddof=1)), color='red')
    ax[1].set(title=f'Residues {y}', xlabel='residue')

    # 3. Normal QQ-plot (line 0 = points, line 1 = reference line)
    stats.probplot(residues, dist='norm', plot=ax[2])
    ax[2].get_lines()[0].set(markersize=3, color='black')
    ax[2].get_lines()[1].set(color='red')
    ax[2].set_title(f'QQ-plot residues (KSL D = {r['KSL_D']:.4f}, p = {r["KSL_p"]:.4f})')

    fig.tight_layout()
    folder.mkdir(parents=True, exist_ok=True)
    # File name safe for the filesystem (no spaces or slashes)
    path = folder / f'{r['sheet']}_{y}'.replace(' ', '_').replace('/', '_')
    path = path.with_suffix('.png')
    fig.savefig(path, dpi=300)
    plt.close()
    return path
