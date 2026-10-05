"""
 * author Antonio Sirignano
 * created on 04-10-2026-15h-36m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import pandas as pd
import numpy as np
import scipy.stats as stats
import matplotlib.pyplot as plt

from pathlib import Path

def parse_log(file_path):
    path = Path(file_path)

    columns = ['r', 'b', 'swpd', 'free', 'buff', 'cache', 'si', 'so',
                'bi', 'bo', 'in', 'cs', 'us', 'sy', 'id', 'wa','st'
                ]
    cleaned = []

    with open(path, 'r') as f:
        for line in f:
            sline = line.strip()
            if not sline or 'procs' in sline or 'swpd' in sline or 'r b' in sline:
                continue
            chunks = sline.split()
            if len(chunks) >= 17:
                cleaned.append(chunks[:17])

    df = pd.DataFrame(cleaned, columns=columns)
    df = df.map(lambda x: str(x).replace(',', '.') if isinstance(x, str) else x)
    return df.apply(pd.to_numeric, errors='coerce').dropna()

def compare_workloads(real_path='report_LL_real.txt', synth_path='report_LL_synthetic.txt'):
    df_real = parse_log(real_path)
    df_synth = parse_log(synth_path)

    metrics = ['cs', 'us', 'sy', 'free']
    comparison_data = []

    for m in metrics:
        mean_r = df_real[m].mean()
        mean_s = df_synth[m].mean()
        rel_err = abs(mean_r - mean_s) / mean_r * 100 if mean_r != 0 else 0

        ks_stat, p_value = stats.ks_2samp(df_real[m], df_synth[m])

        comparison_data.append({
            'Metric': m,
            'Real Mean': round(mean_r, 2),
            'Synth Mean': round(mean_s, 2),
            'Relative Error (%)': round(rel_err, 2),
            'KS Stat (D)': round(ks_stat, 4),
            'p-value': f'{p_value:.4f}' 
        })

    comp_df = pd.DataFrame(comparison_data)

    fig, ax = plt.subplots(figsize=(9, 5))

    r_sorted = np.sort(df_real['cs'])
    r_ecdf = np.arange(1, len(r_sorted) + 1) / len(r_sorted)
    ax.plot(r_sorted, 
            r_ecdf,
            label='Real Workload',
            color='blue',
            linestyle='--',
            linewidth=2,
            )

    s_sorted = np.sort(df_synth['cs'])
    s_ecdf = np.arange(1, len(s_sorted) + 1) / len(s_sorted)
    ax.plot(s_sorted, 
            s_ecdf,
            label='Synthetic Workload',
            color='orange',
            linestyle='--',
            linewidth=2,
            )
    
    ax.set_title('Workload Validation - Context Switches CDF Comparison')
    ax.set_xlabel('Context Switches / sec (cs)')
    ax.set_ylabel('Cumulative Probability F(x)')
    ax.legend()
    ax.grid(True, linestyle=':', alpha=0.6)

    plt.tight_layout()
    plt.savefig('workload_validation_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()

    return comp_df

if __name__ == '__main__':
    report_df = compare_workloads(real_path='/Users/antoniosirignano/Desktop/Progetto Impianti di Elaborazione/03 - Workload Characterization/report_LL_real.txt',
                                  synth_path='/Users/antoniosirignano/Desktop/Progetto Impianti di Elaborazione/03 - Workload Characterization/report_LL_synthetic.txt')
    print('\n WORKLOAD VALIDATION TABLE: REAL VS SYNTHETIC ===')
    print(report_df.to_string(index=False))