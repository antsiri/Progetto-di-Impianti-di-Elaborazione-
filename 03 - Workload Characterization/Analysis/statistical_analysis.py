"""
Statistical analysis of the real workload (low-level vmstat report).

Computes the Pearson correlation matrix of the main KPIs, the temporal
autocorrelation of context switches and fits several candidate distributions
to the context-switch data, choosing the best one with the Kolmogorov-Smirnov
test. Saves ``statistical_distributions.png`` (PDF fit and CDF comparison).
"""

import pandas as pd
import numpy as np
import scipy.stats as stats
import matplotlib.pyplot as plt
from pathlib import Path


def workload_statistical_analysis(file_path):
    """
    Run correlation, autocorrelation and goodness-of-fit analysis on a vmstat log.

    Args:
        file_path (str | Path): path of the vmstat log.

    Returns:
        tuple: ``(corr_matrix, autocorr, gof_results, best_dist_name)`` where
            * ``corr_matrix`` is the Pearson correlation of the KPIs;
            * ``autocorr`` maps ``"Lag-<k>s"`` to the autocorrelation of ``cs``;
            * ``gof_results`` maps each distribution to its fitted parameters,
              KS statistic D and p-value;
            * ``best_dist_name`` is the distribution with the smallest D.

    Raises:
        ValueError: if no valid row is found or all data is NaN.
    """
    path = Path(file_path)

    columns = ['r', 'b', 'swpd', 'free', 'buff', 'cache', 'si', 'so',
               'bi', 'bo', 'in', 'cs', 'us', 'sy', 'id', 'wa', 'st']
    cleaned = []

    with open(path, 'r') as file:
        for line in file:
            sline = line.strip()
            # Skip empty lines and vmstat headers
            if not sline or 'procs' in sline or 'swpd' in sline or 'r  b' in sline:
                continue

            parts = sline.split()

            if len(parts) >= 17:
                cleaned.append(parts[:17])

    if not cleaned:
        raise ValueError(f"No valid rows found in {path.name}.")

    df = pd.DataFrame(cleaned, columns=columns)

    # Handle decimal commas (locale-dependent output) before numeric conversion
    df = df.map(lambda x: str(x).replace(',', '.') if isinstance(x, str) else x)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    kpi = ['cs', 'us', 'sy', 'free']
    df_kpi = df[kpi].dropna()

    if df_kpi.empty:
        raise ValueError("All data are dropped because considered NaN.")

    # 1. Pearson correlation among KPIs
    corr_matrix = df_kpi.corr()

    # 2. Autocorrelation of context switches at different lags (seconds)
    autocorr = {f'Lag-{k}s': df_kpi['cs'].autocorr(lag=k) for k in [1, 5, 10, 30]}

    cs_data = df_kpi['cs'].to_numpy(dtype=np.float64)

    # 3. Candidate theoretical distributions for the context switches
    candidate_dists = {
        'Normal': stats.norm,
        'Gamma': stats.gamma,
        'Lognormal': stats.lognorm,
        'Exponential': stats.expon
    }

    gof_results = {}
    for name, dist in candidate_dists.items():
        # Maximum-likelihood fit of the distribution parameters
        params = dist.fit(cs_data)

        # KS test against the fitted CDF (default args bind the current dist/params)
        ks_stat, p_value = stats.kstest(cs_data, lambda x, d=dist, p=params: d.cdf(x, *p))

        gof_results[name] = {
            'Parameters': params,
            'Statistic_D': ks_stat,
            'p_value': p_value
        }

    # Best model = smallest KS distance D
    best_dist_name = min(gof_results, key=lambda k: gof_results[k]['Statistic_D'])

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # PDF: empirical histogram overlaid with every fitted density
    axes[0].hist(cs_data, bins=35, density=True, alpha=0.5, color='gray', label='Empirical Histogram')
    x = np.linspace(cs_data.min(), cs_data.max(), 1000)

    for name, dist in candidate_dists.items():
        params = gof_results[name]['Parameters']
        pdf = dist.pdf(x, *params)
        axes[0].plot(x, pdf, linewidth=2, label=f'{name}')

    axes[0].set_title('Fitting Probability Density Function (PDF) - Context Switches')
    axes[0].set_xlabel('Context Switches / sec (cs)')
    axes[0].set_ylabel('Probability Density Function')
    axes[0].legend()
    axes[0].grid(True, linestyle=':', alpha=0.6)

    # CDF: empirical CDF vs CDF of the best-fitting model
    best_params = gof_results[best_dist_name]['Parameters']
    best_dist = candidate_dists[best_dist_name]

    sorted_data = np.sort(cs_data)
    ecdf = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
    cdf_fit = best_dist.cdf(sorted_data, *best_params)

    axes[1].plot(sorted_data, ecdf, label='Empirical CDF (ECDF)', color='blue', linewidth=1.5)
    axes[1].plot(sorted_data, cdf_fit, label=f'Theorical CDF Best Fit ({best_dist_name})', color='red', linestyle='--', linewidth=2)
    axes[1].set_title(f'CDF Empirica vs Therical Model ({best_dist_name})')
    axes[1].set_xlabel('Context Switches / sec (cs)')
    axes[1].set_ylabel('Cumulative Probability F(x)')
    axes[1].legend()
    axes[1].grid(True, linestyle=':', alpha=0.6)

    plt.tight_layout()
    plt.savefig('statistical_distributions.png', dpi=300, bbox_inches='tight')
    plt.close()

    return corr_matrix, autocorr, gof_results, best_dist_name


if __name__ == "__main__":
    file_log = "/Users/antoniosirignano/Desktop/Progetto Impianti di Elaborazione/03 - Workload Characterization/report_LL_real.txt"
    corr, auto_c, gof, best_mod = workload_statistical_analysis(file_log)

    print("\n=== CORRELATION MATRIX (PEARSON) ===")
    print(corr.round(4).to_string())
    print("\n=== TEMPORAL AUTOCORRELATION (CS) ===")
    for k, v in auto_c.items():
        print(f"{k}: {v:.4f}")
    print("\n=== TEST GOODNESS-OF-FIT (KOLMOGOROV-SMIRNOV) ===")
    for dist, res in gof.items():
        print(f"Model {dist:<12} | Statistic D: {res['Statistic_D']:.5f} | p-value: {res['p_value']:.5e}")
    print(f"\nBest theorical model identified: {best_mod}")
