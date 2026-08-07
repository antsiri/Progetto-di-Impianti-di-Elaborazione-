import os
import re
import pandas as pd
import matplotlib.pyplot as plt

ITERATIONS = 3

plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

def parse_jmeter_jtl(file_path):
    """Analisi e riordino dati di ALTO LIVELLO (JMeter)"""
    if not os.path.exists(file_path):
        return None, None

    df = pd.read_csv(file_path)
    if df.empty or 'timeStamp' not in df.columns:
        return None, None

    # Ordinamento cronologico fondamentale per evitare linee intrecciate
    df = df.sort_values('timeStamp').reset_index(drop=True)
    
    total_reqs = len(df)
    success_count = (df['responseCode'] == 200).sum() if 'responseCode' in df.columns else df['success'].sum()
    error_rate = ((total_reqs - success_count) / total_reqs) * 100 if total_reqs > 0 else 0
    
    avg_rt = df['elapsed'].mean()
    p90_rt = df['elapsed'].quantile(0.90)
    p95_rt = df['elapsed'].quantile(0.95)
    
    duration_s = (df['timeStamp'].max() - df['timeStamp'].min()) / 1000.0 if total_reqs > 1 else 1
    throughput = total_reqs / duration_s

    summary = {
        "Total Reqs": total_reqs,
        "Throughput (req/s)": round(throughput, 2),
        "Avg Response Time (ms)": round(avg_rt, 2),
        "P90 Response Time (ms)": round(p90_rt, 2),
        "P95 Response Time (ms)": round(p95_rt, 2),
        "Error Rate (%)": round(error_rate, 2)
    }
    return summary, df

def parse_vmstat_log(file_path):
    """Analisi dati di BASSO LIVELLO (vmstat)"""
    if not os.path.exists(file_path):
        return None, None

    data = []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('procs') or line.startswith('r'):
                continue
            parts = re.split(r'\s+', line)
            if len(parts) >= 17:
                try:
                    data.append([float(p) for p in parts[:17]])
                except ValueError:
                    continue

    if not data:
        return None, None

    cols = ['r', 'b', 'swpd', 'free', 'buff', 'cache', 'si', 'so', 'bi', 'bo', 'in', 'cs', 'us', 'sy', 'id', 'wa', 'st']
    df = pd.DataFrame(data, columns=cols[:len(data[0])])

    summary = {
        "Avg CPU User (%)": round(df['us'].mean(), 2),
        "Avg CPU System (%)": round(df['sy'].mean(), 2),
        "Avg CPU Idle (%)": round(df['id'].mean(), 2),
        "Avg CPU IO-Wait (%)": round(df['wa'].mean(), 2),
        "Max CPU IO-Wait (%)": round(df['wa'].max(), 2),
        "Avg Free RAM (MB)": round(df['free'].mean() / 1024, 2),
        "Avg Context Switches/s": round(df['cs'].mean(), 2)
    }
    return summary, df

def generate_charts(jtl_data_list, vmstat_data_list):
    """Genera grafici puliti e aggregati"""
    fig, axes = plt.subplots(2, 1, figsize=(12, 9), sharex=False)

    # -------------------------------------------------------------------
    # GRAFICO 1: Tempi di Risposta JMeter (Aggregati ogni 5 secondi)
    # -------------------------------------------------------------------
    has_jmeter_data = False
    for idx, df_jmeter in enumerate(jtl_data_list):
        if df_jmeter is not None and not df_jmeter.empty:
            has_jmeter_data = True
            start_time = df_jmeter['timeStamp'].min()
            
            # Tempo relativo in secondi
            df_jmeter['rel_sec'] = (df_jmeter['timeStamp'] - start_time) / 1000.0
            
            # Binning in intervalli di 5s per ammorbidire la curva
            df_jmeter['time_bin'] = (df_jmeter['rel_sec'] // 5) * 5
            aggregated = df_jmeter.groupby('time_bin')['elapsed'].mean().reset_index()

            axes[0].plot(
                aggregated['time_bin'], 
                aggregated['elapsed'], 
                label=f"Iterazione {idx+1} (Media 5s)", 
                linewidth=2
            )
            
    if has_jmeter_data:
        axes[0].set_title("ALTO LIVELLO: Tempi di Risposta Medi JMeter (ms) nel Tempo", fontsize=12, fontweight='bold')
        axes[0].set_xlabel("Tempo dall'inizio del test (Secondi)")
        axes[0].set_ylabel("Response Time Medio (ms)")
        axes[0].grid(True, linestyle='--', alpha=0.6)
        axes[0].legend(loc='upper right')

    # -------------------------------------------------------------------
    # GRAFICO 2: Risorse VM (vmstat) - Ultima iterazione disponibile
    # -------------------------------------------------------------------
    last_vmstat = None
    last_iter_num = 0
    for idx, vm_df in enumerate(reversed(vmstat_data_list)):
        if vm_df is not None and not vm_df.empty:
            last_vmstat = vm_df
            last_iter_num = len(vmstat_data_list) - idx
            break

    if last_vmstat is not None:
        time_axis = range(1, len(last_vmstat) + 1)
        axes[1].plot(time_axis, last_vmstat['us'], label="CPU User (%)", color='#1f77b4', linewidth=1.8)
        axes[1].plot(time_axis, last_vmstat['sy'], label="CPU System (%)", color='#ff7f0e', linewidth=1.8)
        axes[1].plot(time_axis, last_vmstat['wa'], label="CPU I/O Wait (%)", color='#d62728', linewidth=1.8)
        
        axes[1].set_title(f"BASSO LIVELLO: Utilizzo CPU e I/O Wait VM (Iterazione {last_iter_num})", fontsize=12, fontweight='bold')
        axes[1].set_xlabel("Tempo (Secondi)")
        axes[1].set_ylabel("Utilizzo (%)")
        axes[1].grid(True, linestyle='--', alpha=0.6)
        axes[1].legend(loc='upper right')
    else:
        axes[1].text(
            0.5, 0.5, 
            "Dati vmstat non trovati nel Mac.\nScaricali con: scp antonio@192.168.64.3:~/vmstat_iter_*.log ./", 
            ha='center', va='center', fontsize=11, color='#d62728', fontweight='bold'
        )
        axes[1].set_title("BASSO LIVELLO: Utilizzo Risorse VM (Dati Mancanti)", fontsize=12, fontweight='bold')

    plt.tight_layout()
    plt.savefig("performance_analysis.png", dpi=300)
    print("\n[+] Grafico generato correttamente: performance_analysis.png")

def main():
    jtl_dfs, vmstat_dfs = [], []

    print("=========================================================================")
    print("           REPORT COMPLETO PRESTAZIONI (ALTO & BASSO LIVELLO)           ")
    print("=========================================================================\n")

    for i in range(1, ITERATIONS + 1):
        jtl_file = f"results_iter_{i}.jtl"
        vmstat_file = f"vmstat_iter_{i}.log"

        jmeter_sum, df_jtl = parse_jmeter_jtl(jtl_file)
        vmstat_sum, df_vm = parse_vmstat_log(vmstat_file)

        jtl_dfs.append(df_jtl)
        vmstat_dfs.append(df_vm)

        print(f"--- [ ITERAZIONE {i} ] ---")
        if jmeter_sum:
            print("  ▶ METRICHE ALTO LIVELLO (JMeter):")
            for k, v in jmeter_sum.items():
                print(f"    - {k:<25}: {v}")
        else:
            print(f"  ✖ File {jtl_file} non trovato.")

        if vmstat_sum:
            print("  ▶ METRICHE BASSO LIVELLO (VM - vmstat):")
            for k, v in vmstat_sum.items():
                print(f"    - {k:<25}: {v}")
        else:
            print(f"  ✖ File {vmstat_file} non trovato.")
        print()

    generate_charts(jtl_dfs, vmstat_dfs)

if __name__ == "__main__":
    main()