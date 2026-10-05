"""
 * author Antonio Sirignano
 * created on 04-10-2026
 * github: https://github.com/antsiri
 * copyright 2026
"""

import os
import time
import multiprocessing as mp
import numpy as np
import scipy.stats as stats
import pandas as pd
from pathlib import Path

def load_gamma_parameters(file_path):
    path = Path(file_path)
    if not path.exists():
        path = Path('report_LL_real.txt')

    cleaned = []
    with open(path, 'r') as f:
        for line in f:
            sline = line.strip()
            if not sline or 'procs' in sline or 'swpd' in sline or 'r  b' in sline:
                continue
            chunks = sline.split()
            if len(chunks) >= 17:
                cleaned.append(chunks[:17])

    columns = ['r', 'b', 'swpd', 'free', 'buff', 'cache', 'si', 'so', 
               'bi', 'bo', 'in', 'cs', 'us', 'sy', 'id', 'wa', 'st']

    df = pd.DataFrame(cleaned, columns=columns)
    df = df.map(lambda x: str(x).replace(',', '.') if isinstance(x, str) else x)
    cs_data = pd.to_numeric(df['cs'], errors='coerce').dropna().to_numpy(dtype=np.float64)

    if len(cs_data) == 0:
        raise ValueError("Impossibile estrarre i dati di 'cs' dal file di log.")

    fit_params = stats.gamma.fit(cs_data)
    print(f'[INIT] Parametri Gamma estratti (shape, loc, scale): {fit_params}')
    return fit_params

def ipc_worker_process(r_fd, w_fd, iterations_shared, run_event, stop_event):
    """Processo worker dedicato all'I/O intensiva su pipe (genera CS e CPU System)."""
    while not stop_event.is_set():
        if run_event.wait(timeout=0.05):
            iters = iterations_shared.value
            for _ in range(iters):
                if stop_event.is_set():
                    break
                try:
                    os.write(w_fd, b'p')
                    os.read(r_fd, 1)
                except Exception:
                    break
            run_event.clear()

def run_synthetic_workload(duration=300, log_real_path='report_LL_real.txt', num_pairs=4):
    gamma_params = load_gamma_parameters(log_real_path)

    stop_event = mp.Event()
    run_event = mp.Event()
    iterations_shared = mp.Value('i', 0)

    processes = []
    pipes = []

    # Creazione di N coppie di processi worker per saturare i core e superare gli 80k CS/s
    for _ in range(num_pairs):
        r1, w1 = os.pipe()
        r2, w2 = os.pipe()
        pipes.extend([r1, w1, r2, w2])

        p1 = mp.Process(target=ipc_worker_process, args=(r1, w2, iterations_shared, run_event, stop_event))
        p2 = mp.Process(target=ipc_worker_process, args=(r2, w1, iterations_shared, run_event, stop_event))
        
        p1.start()
        p2.start()
        processes.extend([p1, p2])

    print(f"=== AVVIO GENERATORE MULTI-PROCESSO ({num_pairs} COPPIE) - DURATA: {duration}s ===")

    try:
        for sec in range(duration):
            t_start = time.time()

            target_cs = int(stats.gamma.rvs(*gamma_params))
            
            # Ogni ciclo IPC tra 2 processi genera ~2 CS.
            # Il carico viene ripartito equamente tra le coppie di processi attivi.
            total_ipc_cycles = max(1, target_cs // 2)
            cycles_per_pair = max(1, total_ipc_cycles // num_pairs)

            iterations_shared.value = cycles_per_pair
            run_event.set()

            if (sec + 1) % 30 == 0:
                print(f"[PROGRESSO] Generati {sec + 1}/{duration}s | Target CS: {target_cs}")

            elapsed = time.time() - t_start
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)

    finally:
        stop_event.set()
        run_event.set()
        
        for p in processes:
            p.join(timeout=1.0)
            if p.is_alive():
                p.terminate()

        for fd in pipes:
            try:
                os.close(fd)
            except OSError:
                pass

        print('=== GENERAZIONE COMPLETATA ===')

if __name__ == "__main__":
    run_synthetic_workload(duration=900)
