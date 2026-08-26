import os
import re
import pandas as pd
import matplotlib.pyplot as plt

ITERATIONS = 3
# Colore personalizzato per la linea della MEDIA: RGB (0.0, 0.2, 0.4)
MEAN_COLOR = (0.0, 0.2, 0.4)

# Stile grafico
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

def parse_jmeter_jtl(file_path):
    """Analisi dati di ALTO LIVELLO (JMeter) per singola iterazione"""
    if not os.path.exists(file_path):
        return None, None

    df = pd.read_csv(file_path)
    if df.empty or 'timeStamp' not in df.columns:
        return None, None

    df = df.sort_values('timeStamp').reset_index(drop=True)
    start_time = df['timeStamp'].min()
    df['rel_sec'] = (df['timeStamp'] - start_time) / 1000.0

    total_reqs = len(df)
    success_count = (df['responseCode'] == 200).sum() if 'responseCode' in df.columns else df['success'].sum()
    error_rate = ((total_reqs - success_count) / total_reqs) * 100 if total_reqs > 0 else 0
    duration_s = (df['timeStamp'].max() - start_time) / 1000.0 if total_reqs > 1 else 1
    throughput = total_reqs / duration_s

    summary = {
        "Total Reqs": total_reqs,
        "Throughput (req/s)": round(throughput, 2),
        "Avg Response Time (ms)": round(df['elapsed'].mean(), 2),
        "P90 Response Time (ms)": round(df['elapsed'].quantile(0.90), 2),
        "P95 Response Time (ms)": round(df['elapsed'].quantile(0.95), 2),
        "Error Rate (%)": round(error_rate, 2)
    }

    BIN_SIZE = 5
    df['time_bin'] = (df['rel_sec'] // BIN_SIZE) * BIN_SIZE

    agg = df.groupby('time_bin').agg(
        req_count=('elapsed', 'count'),
        avg_rt_ms=('elapsed', 'mean')
    ).reset_index()

    agg['throughput'] = agg['req_count'] / float(BIN_SIZE)
    agg['avg_rt_sec'] = agg['avg_rt_ms'] / 1000.0
    agg['power'] = agg.apply(
        lambda row: row['throughput'] / row['avg_rt_sec'] if row['avg_rt_sec'] > 0 else 0, 
        axis=1
    )

    return summary, agg

def parse_vmstat_log(file_path):
    """Analisi dati di BASSO LIVELLO (vmstat) per singola iterazione"""
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
    df['time_sec'] = range(1, len(df) + 1)

    df['free_mb'] = df['free'] / 1024.0
    df['buff_mb'] = df['buff'] / 1024.0
    df['cache_mb'] = df['cache'] / 1024.0
    df['swpd_mb'] = df['swpd'] / 1024.0

    summary = {
        "Avg CPU User (%)": round(df['us'].mean(), 2),
        "Avg CPU System (%)": round(df['sy'].mean(), 2),
        "Avg CPU Idle (%)": round(df['id'].mean(), 2),
        "Avg CPU IO-Wait (%)": round(df['wa'].mean(), 2),
        "Avg Free RAM (MB)": round(df['free_mb'].mean(), 2),
        "Avg Context Switches/s": round(df['cs'].mean(), 2)
    }

    return summary, df

def generate_high_level_charts(jmeter_data_list):
    """Genera i 3 grafici di Alto Livello con linea della MEDIA colorata in RGB (0.0, 0.2, 0.4)"""
    fig, axes = plt.subplots(3, 1, figsize=(12, 11), sharex=True)
    fig.suptitle("ANALISI AD ALTO LIVELLO - MEDIA & ITERAZIONI (JMeter)", fontsize=14, fontweight='bold')

    valid_dfs = [df for df in jmeter_data_list if df is not None and not df.empty]

    if valid_dfs:
        # Plot singole iterazioni (linee sottili trasparenti)
        for idx, df in enumerate(jmeter_data_list):
            if df is not None and not df.empty:
                axes[0].plot(df['time_bin'], df['throughput'], alpha=0.35, linewidth=1, label=f"Iterazione {idx+1}")
                axes[1].plot(df['time_bin'], df['avg_rt_ms'], alpha=0.35, linewidth=1)
                axes[2].plot(df['time_bin'], df['power'], alpha=0.35, linewidth=1)

        # Calcolo MEDIA tra le iterazioni
        combined = pd.concat(valid_dfs)
        df_mean = combined.groupby('time_bin').mean().reset_index()

        # Plot MEDIA (Linea in grassetto con colore RGB 0.0, 0.2, 0.4)
        axes[0].plot(df_mean['time_bin'], df_mean['throughput'], color=MEAN_COLOR, linewidth=2.5, label='MEDIA 3 ITERAZIONI')
        axes[1].plot(df_mean['time_bin'], df_mean['avg_rt_ms'], color=MEAN_COLOR, linewidth=2.5, label='MEDIA 3 ITERAZIONI')
        axes[2].plot(df_mean['time_bin'], df_mean['power'], color=MEAN_COLOR, linewidth=2.5, label='MEDIA 3 ITERAZIONI')

        axes[0].set_title("1. Throughput (Richieste/secondo)", fontweight='bold')
        axes[0].set_ylabel("Throughput (req/s)")
        axes[0].grid(True, linestyle='--', alpha=0.6)
        axes[0].legend(loc='upper right')

        axes[1].set_title("2. Response Time Medio (ms)", fontweight='bold')
        axes[1].set_ylabel("Tempo (ms)")
        axes[1].grid(True, linestyle='--', alpha=0.6)
        axes[1].legend(loc='upper right')

        axes[2].set_title("3. System Power (Throughput / RT [sec])", fontweight='bold')
        axes[2].set_xlabel("Tempo dall'inizio del test (Secondi)")
        axes[2].set_ylabel("Power (req/s²)")
        axes[2].grid(True, linestyle='--', alpha=0.6)
        axes[2].legend(loc='upper right')

    plt.tight_layout()
    plt.savefig("high_level_performance.png", dpi=300)
    print("[+] Grafico Alto Livello salvato: high_level_performance.png")

def generate_low_level_charts(vmstat_data_list):
    """Genera i grafici di Basso Livello sulla MEDIA delle 3 iterazioni"""
    valid_dfs = [df for df in vmstat_data_list if df is not None and not df.empty]

    fig, axes = plt.subplots(4, 1, figsize=(12, 14), sharex=True)

    if valid_dfs:
        combined = pd.concat(valid_dfs)
        df_mean = combined.groupby('time_sec').mean().reset_index()

        fig.suptitle("ANALISI A BASSO LIVELLO - MEDIA 3 ITERAZIONI (vmstat Bottlenecks)", fontsize=14, fontweight='bold')

        # 1. CPU
        axes[0].plot(df_mean['time_sec'], df_mean['us'], label='User CPU (%)', color='#1f77b4', linewidth=2)
        axes[0].plot(df_mean['time_sec'], df_mean['sy'], label='System Kernel CPU (%)', color='#ff7f0e', linewidth=2)
        axes[0].plot(df_mean['time_sec'], df_mean['wa'], label='I/O Wait CPU (%)', color='#d62728', linewidth=2.5, linestyle='--')
        axes[0].plot(df_mean['time_sec'], df_mean['id'], label='Idle CPU (%)', color='#2ca02c', linewidth=1, alpha=0.5)
        axes[0].set_title("1. CPU Saturation & I/O Wait Bottleneck (Media)", fontweight='bold')
        axes[0].set_ylabel("CPU (%)")
        axes[0].grid(True, linestyle='--', alpha=0.6)
        axes[0].legend(loc='upper right')

        # 2. Disk I/O
        ax2_twin = axes[1].twinx()
        axes[1].plot(df_mean['time_sec'], df_mean['bi'], label='Blocks In (bi)', color='#9467bd', linewidth=1.8)
        axes[1].plot(df_mean['time_sec'], df_mean['bo'], label='Blocks Out (bo)', color='#8c564b', linewidth=1.8)
        ax2_twin.plot(df_mean['time_sec'], df_mean['wa'], label='I/O Wait (%)', color='#d62728', linestyle=':', linewidth=2)
        
        # Limite fisso per l'asse I/O Wait (0% - 100%)
        ax2_twin.set_ylim(0, 100)
        
        axes[1].set_title("2. Disk I/O Throughput vs I/O Wait (Media)", fontweight='bold')
        axes[1].set_ylabel("Blocks / s")
        ax2_twin.set_ylabel("I/O Wait (%)", color='#d62728')
        axes[1].grid(True, linestyle='--', alpha=0.6)
        lines1, labels1 = axes[1].get_legend_handles_labels()
        lines2, labels2 = ax2_twin.get_legend_handles_labels()
        axes[1].legend(lines1 + lines2, labels1 + labels2, loc='upper right')

        # 3. Memory
        axes[2].plot(df_mean['time_sec'], df_mean['free_mb'], label='Free RAM (MB)', color='#2ca02c', linewidth=2)
        axes[2].plot(df_mean['time_sec'], df_mean['buff_mb'], label='Buffer RAM (MB)', color='#17becf', linewidth=2)
        axes[2].plot(df_mean['time_sec'], df_mean['cache_mb'], label='Cache RAM (MB)', color='#bcbd22', linewidth=2)
        axes[2].plot(df_mean['time_sec'], df_mean['swpd_mb'], label='Used Swap (MB)', color='#e377c2', linewidth=2, linestyle='--')
        axes[2].set_title("3. Memory Allocation & Swap Usage (Media)", fontweight='bold')
        axes[2].set_ylabel("Memoria (MB)")
        axes[2].grid(True, linestyle='--', alpha=0.6)
        axes[2].legend(loc='upper right')

        # 4. Scheduling
        ax4_twin = axes[3].twinx()
        axes[3].plot(df_mean['time_sec'], df_mean['r'], label='Runnable Procs (r)', color='#1f77b4', linewidth=2)
        axes[3].plot(df_mean['time_sec'], df_mean['b'], label='Blocked Procs (b)', color='#d62728', linewidth=2)
        ax4_twin.plot(df_mean['time_sec'], df_mean['cs'], label='Context Switches/s (cs)', color='#7f7f7f', linestyle=':', alpha=0.8)
        axes[3].set_title("4. Process Queue & Context Switches (Media)", fontweight='bold')
        axes[3].set_xlabel("Tempo (Secondi)")
        axes[3].set_ylabel("Num Processi")
        ax4_twin.set_ylabel("CS / s", color='#7f7f7f')
        axes[3].grid(True, linestyle='--', alpha=0.6)
        lines1, labels1 = axes[3].get_legend_handles_labels()
        lines2, labels2 = ax4_twin.get_legend_handles_labels()
        axes[3].legend(lines1 + lines2, labels1 + labels2, loc='upper right')

    else:
        fig.suptitle("ANALISI A BASSO LIVELLO (Dati vmstat Mancanti)", fontsize=14, fontweight='bold')
        axes[0].text(0.5, 0.5, "File vmstat non trovati.\nScaricali con: scp antonio@192.168.64.3:~/vmstat_iter_*.log ./", ha='center', va='center')

    plt.tight_layout()
    plt.savefig("low_level_bottlenecks.png", dpi=300)
    print("[+] Grafico Basso Livello salvato: low_level_bottlenecks.png")

def main():
    jtl_summaries, vmstat_summaries = [], []
    jtl_dfs, vmstat_dfs = [], []

    print("=========================================================================")
    print("           REPORT PRESTAZIONI: SINGOLE ITERAZIONI & MEDIA               ")
    print("=========================================================================\n")

    for i in range(1, ITERATIONS + 1):
        jtl_file = f"results_iter_{i}.jtl"
        vmstat_file = f"vmstat_iter_{i}.log"

        j_sum, j_df = parse_jmeter_jtl(jtl_file)
        v_sum, v_df = parse_vmstat_log(vmstat_file)

        if j_sum: jtl_summaries.append(j_sum)
        if v_sum: vmstat_summaries.append(v_sum)

        jtl_dfs.append(j_df)
        vmstat_dfs.append(v_df)

        print(f"--- [ ITERAZIONE {i} ] ---")
        if j_sum:
            print("  ▶ JMeter:")
            for k, v in j_sum.items(): print(f"    - {k:<25}: {v}")
        if v_sum:
            print("  ▶ vmstat:")
            for k, v in v_sum.items(): print(f"    - {k:<25}: {v}")
        print()

    print("=========================================================================")
    print("                       MEDIA SULLE 3 ITERAZIONI                          ")
    print("=========================================================================")

    if jtl_summaries:
        df_j_sum = pd.DataFrame(jtl_summaries)
        print("  ▶ METRICHE DI ALTO LIVELLO (JMeter) - MEDIA:")
        for col in df_j_sum.columns:
            print(f"    - {col:<25}: {round(df_j_sum[col].mean(), 2)}")
        print()

    if vmstat_summaries:
        df_v_sum = pd.DataFrame(vmstat_summaries)
        print("  ▶ METRICHE DI BASSO LIVELLO (vmstat) - MEDIA:")
        for col in df_v_sum.columns:
            print(f"    - {col:<25}: {round(df_v_sum[col].mean(), 2)}")
        print()

    generate_high_level_charts(jtl_dfs)
    generate_low_level_charts(vmstat_dfs)

if __name__ == "__main__":
    main()