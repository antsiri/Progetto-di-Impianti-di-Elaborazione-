"""
 * author Antonio Sirignano
 * created on 03-10-2026-09h-37m
 * github: https://github.com/antsiri
 * copyright 2026

Descriptive analysis of a low-level vmstat report.

Computes summary statistics (mean, std, percentiles) of the main KPIs and
saves ``workload_profile.png`` with the context-switch time series and the
CPU usage profile.
"""

import pandas as pd
import matplotlib.pyplot as plt


def vmstat_report_analyze(file_path):
    """
    Parse a vmstat log and compute KPI statistics and plots.

    Args:
        file_path (str): path of the vmstat log.

    Returns:
        tuple[pandas.DataFrame, pandas.DataFrame]: the parsed samples and the
        statistics table (one row per KPI, plus the ``sys/us ratio`` row).
    """
    # Standard vmstat column names
    columns = ['r', 'b', 'swpd', 'free', 'buff', 'cache', 'si', 'so',
                'bi', 'bo', 'in', 'cs', 'us', 'sy', 'id', 'wa','st'
                ]
    cleaned = []

    with open(file_path, 'r') as f:
        for line in f:
            # Skip header lines and empty lines
            if 'procs' in line or 'swpd'in line or line.strip() == '':
                continue

            chunks = line.strip().split()

            # Keep only complete rows (17 fields)
            if len(chunks) >= 17:
                cleaned.append(chunks[:17])

    df = pd.DataFrame(cleaned, columns=columns).apply(pd.to_numeric, errors='coerce')

    # KPIs of interest: context switches, CPU breakdown, free memory, swap
    kpi = ['cs', 'us', 'sy', 'id', 'wa', 'free', 'swpd']

    stats = df[kpi].describe(percentiles=[0.5, 0.95, 0.99]).T
    stats = stats[['mean', 'std', 'min', '50%', '95%', '99%', 'max']]
    stats.columns = ['Mean', 'Std.Dev', 'Min', 'Median (p50)', 'p95', 'p99', 'Max']

    # Kernel vs user CPU ratio (guard against division by zero)
    stats.loc['sys/us ratio', 'Mean'] = df['sy'].mean() / (df['us'].mean() if df['us'].mean() > 0 else 1)

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # Top: context switches with mean and p95 reference lines
    axes[0].plot(df.index, df['cs'], color='#1f77b4', linewidth=1, label='Context Switches (cs)')
    axes[0].axhline(df['cs'].mean(), color='red', linestyle='--', label=f"Mean: {df['cs'].mean():.1f}")
    axes[0].axhline(df['cs'].quantile(0.95), color='orange', linestyle=':', label=f"p95: {df['cs'].quantile(0.95):.1f}")
    axes[0].set_ylabel('CS / second')
    axes[0].set_title('Workload Characterization - Time Series Context Switches')
    axes[0].legend(loc='upper right')
    axes[0].grid(True, linestyle=':', alpha=0.6)

    # Bottom: CPU profile (user, system, I/O wait)
    axes[1].plot(df.index, df['us'], label='User CPU (us)', color='#2ca02c', alpha=0.8)
    axes[1].plot(df.index, df['sy'], label='System CPU (sy)', color='#d62728', alpha=0.8)
    axes[1].plot(df.index, df['wa'], label='I/O Wait (wa)', color='#9467bd', alpha=0.8)
    axes[1].set_xlabel('Time (Sampoles per second)')
    axes[1].set_ylabel('CPU Use (%)')
    axes[1].set_title('Workload Characterization - CPU profile')
    axes[1].legend(loc='upper right')
    axes[1].grid(True, linestyle=':', alpha=0.6)

    plt.tight_layout()
    plt.savefig('workload_profile.png', dpi=300)
    plt.close()

    return df, stats


if __name__ == '__main__':
    # Low-level report collected during the real workload
    file_log = '/Users/antoniosirignano/Desktop/Progetto Impianti di Elaborazione/03 - Workload Characterization/report_LL_real.txt'

    df, summary = vmstat_report_analyze(file_log)

    print('--- SUMMARY ---')
    print(summary.to_string())
