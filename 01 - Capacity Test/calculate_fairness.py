"""
 * author Antonio Sirignano
 * created on 07-08-2026-11h-15m
 * github: https://github.com/antsiri
 * copyright 2026

Jain's Fairness Index analysis of the capacity test results.

Computes the index both *intra-iteration* (how evenly requests and bandwidth
are shared among JMeter threads / samplers) and *inter-iteration* (how
repeatable throughput and bandwidth are across iterations).
"""

import os
import pandas as pd
import numpy as np


def calculate_jains_fairness(values):
    """
    Compute Jain's Fairness Index for a series of numeric values.

    Formula: ``J = (sum(x)^2) / (n * sum(x^2))``

    Args:
        values (array-like): non-negative values (e.g. requests per thread).

    Returns:
        float: value between 1/n (minimum fairness) and 1.0 (maximum
        fairness), rounded to 4 decimals; 0.0 for empty or all-zero input.
    """
    vals = np.array(values, dtype=float)
    n = len(vals)
    # Degenerate case: no values or all zero -> index undefined, return 0
    if n == 0 or np.sum(vals) == 0:
        return 0.0
    sum_x = np.sum(vals)
    sum_sq_x = np.sum(vals ** 2)
    return round(float((sum_x ** 2) / (n * sum_sq_x)), 4)


def calculate_fairness_for_iterations(jtl_files):
    """
    Print Jain's Fairness Index report for a list of JMeter result files.

    For every iteration it reports total throughput/bandwidth and the index
    computed per thread (requests and bytes) and per sampler label. Then it
    computes the inter-iteration index on throughput and bandwidth.

    Args:
        jtl_files (list[str]): paths of the ``.jtl`` files, one per iteration.
    """
    print("=========================================================================")
    print("           ANALISI JAIN'S FAIRNESS INDEX (3 ITERAZIONI)                  ")
    print("=========================================================================\n")

    # Per-iteration totals, used later for the inter-iteration index
    iteration_throughputs = []
    iteration_bandwidths = []

    print("1. FAIRNESS INTRA-ITERAZIONE (Ripartizione risorse tra Thread/Gruppi):")
    print("-" * 73)

    for idx, file_path in enumerate(jtl_files, start=1):
        if not os.path.exists(file_path):
            print(f"[!] File '{file_path}' non trovato. Salto iterazione {idx}.")
            continue

        df = pd.read_csv(file_path)
        if df.empty or 'timeStamp' not in df.columns:
            continue

        # Test duration in seconds
        duration_s = (df['timeStamp'].max() - df['timeStamp'].min()) / 1000.0
        if duration_s <= 0:
            duration_s = 1.0

        total_reqs = len(df)
        total_bytes = df['bytes'].sum() if 'bytes' in df.columns else 0

        # Iteration throughput (req/s) and bandwidth (MB/s)
        iter_tp = total_reqs / duration_s
        iter_bw = (total_bytes / (1024.0 * 1024.0)) / duration_s  # MB/s

        iteration_throughputs.append(iter_tp)
        iteration_bandwidths.append(iter_bw)

        # A) Fairness per single thread (requests and bandwidth)
        thread_stats = df.groupby('threadName').agg(
            req_count=('elapsed', 'count'),
            bytes_sum=('bytes', 'sum') if 'bytes' in df.columns else ('elapsed', lambda x: 0)
        )

        jain_thread_reqs = calculate_jains_fairness(thread_stats['req_count'].values)

        if 'bytes' in df.columns and thread_stats['bytes_sum'].sum() > 0:
            jain_thread_bw = calculate_jains_fairness(thread_stats['bytes_sum'].values)
        else:
            jain_thread_bw = "N/A (Colonna 'bytes' assente)"

        # B) Fairness among thread groups / labels (heterogeneous requests)
        if 'label' in df.columns and df['label'].nunique() > 1:
            group_stats = df.groupby('label').agg(
                req_count=('elapsed', 'count'),
                bytes_sum=('bytes', 'sum') if 'bytes' in df.columns else ('elapsed', lambda x: 0)
            )
            # Normalise to bandwidth (MB/s for each group)
            group_bw = group_stats['bytes_sum'] / (1024.0 * 1024.0 * duration_s)
            jain_group_bw = calculate_jains_fairness(group_bw.values)
        else:
            jain_group_bw = "N/D (Singolo Sampler/Label)"

        print(f"Iterazione {idx} ({file_path}):")
        print(f"  • Throughput Totale               : {iter_tp:.2f} req/s")
        print(f"  • Bandwidth Totale                : {iter_bw:.2f} MB/s")
        print(f"  • Jain Index (Thread - Richieste) : {jain_thread_reqs}")
        print(f"  • Jain Index (Thread - Bandwidth) : {jain_thread_bw}")
        print(f"  • Jain Index (Tra Gruppi/Label)   : {jain_group_bw}\n")

    # Inter-iteration fairness: a value close to 1 means the test is repeatable
    print("2. FAIRNESS INTER-ITERAZIONE (Ripetibilità del test):")
    print("-" * 73)
    if len(iteration_throughputs) > 1:
        jain_inter_tp = calculate_jains_fairness(iteration_throughputs)
        jain_inter_bw = calculate_jains_fairness(iteration_bandwidths)

        print(f"• Throughput per Iterazione (req/s) : {[round(x, 2) for x in iteration_throughputs]}")
        print(f"• Bandwidth per Iterazione (MB/s)  : {[round(x, 2) for x in iteration_bandwidths]}")
        print(f"• Jain's Fairness Index (Throughput): {jain_inter_tp}")
        print(f"• Jain's Fairness Index (Bandwidth) : {jain_inter_bw}")
    else:
        print("[!] Trovata una sola iterazione valida. Servono almeno 2 file .jtl per la stima inter-iterazione.")


if __name__ == "__main__":
    # Result files of the three capacity test iterations
    jtl_files = ["results_iter_1.jtl", "results_iter_2.jtl", "results_iter_3.jtl"]
    calculate_fairness_for_iterations(jtl_files)
