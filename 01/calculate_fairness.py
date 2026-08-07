"""
 * author Antonio Sirignano
 * created on 07-08-2026-11h-15m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import os
import pandas as pd
import numpy as np

def calculate_jains_fairness(values):
    """
    Calcola l'Indice di Fairness di Jain per una serie di valori numerici.
    Formula: J = (sum(x)^2) / (n * sum(x^2))
    Ritorna un valore compreso tra 1/n (minima equità) e 1.0 (massima equità).
    """
    vals = np.array(values, dtype=float)
    n = len(vals)
    if n == 0 or np.sum(vals) == 0:
        return 0.0
    sum_x = np.sum(vals)
    sum_sq_x = np.sum(vals ** 2)
    return round(float((sum_x ** 2) / (n * sum_sq_x)), 4)

def calculate_fairness_for_iterations(jtl_files):
    print("=========================================================================")
    print("           ANALISI JAIN'S FAIRNESS INDEX (3 ITERAZIONI)                  ")
    print("=========================================================================\n")

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

        # Durata del test in secondi
        duration_s = (df['timeStamp'].max() - df['timeStamp'].min()) / 1000.0
        if duration_s <= 0:
            duration_s = 1.0

        total_reqs = len(df)
        total_bytes = df['bytes'].sum() if 'bytes' in df.columns else 0

        iter_tp = total_reqs / duration_s
        iter_bw = (total_bytes / (1024.0 * 1024.0)) / duration_s  # MB/s

        iteration_throughputs.append(iter_tp)
        iteration_bandwidths.append(iter_bw)

        # A) Fairness per Singolo Thread (Richieste e Bandwidth)
        thread_stats = df.groupby('threadName').agg(
            req_count=('elapsed', 'count'),
            bytes_sum=('bytes', 'sum') if 'bytes' in df.columns else ('elapsed', lambda x: 0)
        )
        
        jain_thread_reqs = calculate_jains_fairness(thread_stats['req_count'].values)
        
        if 'bytes' in df.columns and thread_stats['bytes_sum'].sum() > 0:
            jain_thread_bw = calculate_jains_fairness(thread_stats['bytes_sum'].values)
        else:
            jain_thread_bw = "N/A (Colonna 'bytes' assente)"

        # B) Fairness tra Thread Groups / Label (Richieste eterogenee)
        if 'label' in df.columns and df['label'].nunique() > 1:
            group_stats = df.groupby('label').agg(
                req_count=('elapsed', 'count'),
                bytes_sum=('bytes', 'sum') if 'bytes' in df.columns else ('elapsed', lambda x: 0)
            )
            # Normalizzazione per Bandwidth (MB/s per ciascun gruppo)
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
    jtl_files = ["results_iter_1.jtl", "results_iter_2.jtl", "results_iter_3.jtl"]
    calculate_fairness_for_iterations(jtl_files)