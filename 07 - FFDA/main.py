import time
from pathlib import Path
import numpy as np

# Import dai moduli del progetto
from ffda.Logger.mercurylogger import MercuryLogParser
from ffda.ColescenceEngine.colescence import CoalescenceEngine
from ffda.Reliability.reliability import ReliabilityAnalyzer
from ffda.Reliability.visualizer import ReliabilityVisualizer
from ffda.Monitor.monitor import FileTailMonitor, LogFilterEngine


def generate_sample_syslog(output_file: Path, num_episodes: int = 500):
    print(f"[*] File {output_file} not found.")
    print(f"[*] Generation of {num_episodes} episods...")
    
    categories = ["DEV", "MEM", "I-O", "NET", "PRO", "OTH"]
    nodes = ["tg-c401", "tg-master", "tg-c572", "tg-s044", "tg-c238"]
    
    current_time = 1000.0
    
    with open(output_file, "w", encoding="utf-8") as f:
        for _ in range(num_episodes):
            if np.random.rand() < 0.4:
                ttf = np.random.exponential(scale=1000)   # TTF brevi (> CWIN)
            else:
                ttf = np.random.exponential(scale=10000)  # TTF lunghi
            
            current_time += ttf
            
            burst_size = np.random.randint(50, 250)
            burst_node = np.random.choice(nodes, p=[0.75, 0.08, 0.07, 0.05, 0.05])
            burst_cat = np.random.choice(categories, p=[0.70, 0.16, 0.07, 0.04, 0.02, 0.01])
            
            for _ in range(burst_size):
                delta_burst = np.random.uniform(0.01, 1.5)
                current_time += delta_burst
                
                raw_line = f"FATAL ERROR on {burst_node}: {burst_cat} hardware failure"
                formatted = LogFilterEngine.filter_and_format(raw_line, default_node=burst_node)
                
                if formatted:
                    parts = formatted.split()
                    parts[0] = f"{current_time:.0f}"
                    f.write(" ".join(parts) + "\n")

    print(f"[✓] File '{output_file}' generated successfully.\n")


def main():
    log_file = Path("mercury_syslog.log")
    if not log_file.exists():
        generate_sample_syslog(log_file, num_episodes=200000)
    else:
        print(f"[i] Log file '{log_file}' already exists. Monitor skipped.\n")

    # ==========================================
    # 2. PARSING DEL LOG
    # ==========================================
    print(f"[*] Parsing lof file: {log_file}...")
    parser = MercuryLogParser(str(log_file))
    entries = parser.parse()
    print(f"[✓] Loaded {len(entries)} events.")

    if not entries:
        print("[!] No data found. Interruption.")
        return

    # ==========================================
    # 3. ANALISI DI SENSITIVITÀ CWIN
    # ==========================================
    print("[*] Execution CWIN Sensitivity Analysis ...")
    coalescer = CoalescenceEngine()
    cwin_range = [10, 30, 50, 75, 100, 150, 200, 230, 300, 500, 800]
    sensitivity_dict = coalescer.sensitivity_analysis(entries, cwin_range)

    # Salva il grafico della CWIN
    ReliabilityVisualizer.plot_sensitivity(
        sensitivity_dict, 
        chosen_cwin=200, 
        filename="cwin_sensitivity.png"
    )
    print("[✓] Plot CWIN saved in 'cwin_sensitivity.png'.")

    # ==========================================
    # 4. TUPLING CON CWIN SELEZIONATA (200s)
    # ==========================================
    chosen_cwin = 200
    tuples = coalescer.tuple_logs(entries, cwin=chosen_cwin)
    print(f"[✓] Generated {len(tuples)} tuples with CWIN={chosen_cwin}s.")

    ttf_samples = coalescer.calculate_inter_arrival_times(tuples)
    if len(ttf_samples) < 2:
        print("[!] Sample TTF not enough for the fitting.")
        return

    # ==========================================
    # 5. CALCOLO RELIABILITY EMPIRICA E FITTING
    # ==========================================
    analyzer = ReliabilityAnalyzer()
    t_vals, r_emp = analyzer.compute_empirical_reliability(ttf_samples)

    # Fit Iper-esponenziale
    hyp_fit = analyzer.fit_model("hyperexponential", t_vals, r_emp)

    print("\n--- RESULTS IPER-EXPONENTIAL REGREESSION ---")
    print(f"R²: {hyp_fit['r_squared']:.5f}")
    print(f"SSE: {hyp_fit['sse']:.5f}")
    print(f"p-value (K-S Test): {hyp_fit['p_value']:.4f}")

    # ==========================================
    # 6. CALCOLO MTTF ED ESPORTAZIONE GRAFICI
    # ==========================================
    mttf = analyzer.calculate_mttf(hyp_fit["predict_func"])
    print(f"MTTF Stimato: {mttf:.2f} secondi ({mttf / 3600:.2f} ore)\n")

    ReliabilityVisualizer.plot_reliability_fit(
        t_vals, 
        r_emp, 
        hyp_fit, 
        title="Fit Plot - Hyperexponential", 
        filename="reliability_fit.png"
    )
    print("[✓] Plt Reliability saved in 'reliability_fit.png'.")


if __name__ == "__main__":
    main()