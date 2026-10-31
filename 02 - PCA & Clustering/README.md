# PCA & Clustering

Workload characterization completa di un Web Server: generazione di un workload reale,
misure HL (richieste HTTP) e LL (metriche di sistema e di processo), PCA + clustering
gerarchico, costruzione di un workload sintetico e confronto statistico tra i due carichi.

## Procedura

1. **Raccolta dati (reale)**: server FastAPI che serve 24 file binari casuali divisi in
   5 categorie di taglia (`low` … `high`); il load generator invia richieste pesate per
   categoria mentre il collector (`psutil`) registra le metriche LL ogni secondo
2. **Pulizia**: statistiche per colonna, istogramma + boxplot, segnalazione di colonne a
   bassa cardinalità (< 1%) e righe con |z| > 4; rimozione manuale di colonne costanti e
   dei transienti di ramp-up / cool-down
3. **PCA + clustering**: standardizzazione, PCA, sweep (n. componenti × n. cluster) con
   clustering gerarchico di Ward e calcolo della devianza persa
4. **HL a blocchi**: il dataset HL (~679k righe) non entra in un clustering O(n²), quindi
   si usa una pipeline incrementale: `StandardScaler.partial_fit` → `IncrementalPCA` →
   CF-tree BIRCH → clustering gerarchico sui sub-cluster → assegnazione finale
5. **Workload sintetico**: tabella di contingenza cluster × risorsa, risorsa più frequente
   per cluster, esclusione dei cluster < 50 osservazioni, pesi normalizzati su 100
6. **Raccolta dati (sintetico)**: stesso server e collector, load generator alimentato
   dalla pool pesata (con think time di 10 ms)
7. **Validazione**: un campione per cluster (osservazione più vicina al centroide),
   test di Kolmogorov-Smirnov e test di Wilcoxon rank-sum, reale vs sintetico

| Dataset | Componenti | Cluster | Devianza persa (reale) | Devianza persa (sintetico) |
|---|---|---|---|---|
| LL globale | 3 | 15 | 0.0566 | 0.0214 |
| LL processo | 2 | 15 | 0.0609 | 0.0400 |
| HL (chunked, 153 sub-cluster BIRCH) | 2 | 15 | 0.0106 | — |

Il test di Wilcoxon non rigetta H₀ su nessuna componente: nessuna evidenza di
differenza tra workload reale e sintetico (con il limite di n = 15).

## Struttura

```
workload-characterization/
├── pyproject.toml
├── orchestrator.py                 avvia collector e load generator in parallelo
├── server/
│   ├── app.py                      server FastAPI (/samples, /health)
│   ├── generate_samples.py         genera i file campione + manifest.csv
│   └── static/                     file campione e manifest.csv
├── load_gen/generator.py           load generator multi-thread pesato (report HL)
├── collector/metrics.py            collector psutil (LL globale e di processo)
├── analysis/
│   ├── clean.py                    ispezione: statistiche, plot, colonne/righe candidate
│   ├── apply_cleaning.py           applica le decisioni di pulizia
│   ├── pca_clustering.py           PCA + clustering (strategia standard o chunked)
│   ├── build_synthetic_workload.py tabella di contingenza e pool pesata
│   ├── extract_samples.py          un campione per cluster nello spazio PCA
│   ├── hypothesis_tests.py         QQ-plot, KS e Wilcoxon reale vs sintetico
│   └── plots/                      grafici e CSV prodotti dall'analisi
├── data/
│   ├── raw/                        report grezzi (hl_report, ll_global, ll_process)
│   └── processed/                  dataset puliti, manifest sintetico, campioni
└── notebooks/notebook.ipynb        verifica degli outlier e costruzione della pool
```

## Uso

Tutti i comandi vanno lanciati da `workload-characterization/`.

```bash
poetry install

# 1. File campione e server
poetry run python -m server.generate_samples
poetry run uvicorn server.app:app --port 8000

# 2. Workload reale (in un altro terminale)
poetry run python orchestrator.py --duration 3600 --threads 15

# 3. Ispezione e pulizia (esempio su LL globale)
poetry run python -m analysis.clean --input data/raw/ll_global.csv
poetry run python -m analysis.apply_cleaning --input data/raw/ll_global.csv \
    --output data/processed/ll_global_clean.csv --drop-columns mem_total \
    --ramp-up 32 --cooldown 23

# 4. PCA + clustering
poetry run python -m analysis.pca_clustering --input data/processed/ll_global_clean.csv
poetry run python -m analysis.pca_clustering --input data/processed/hl_report_clean.csv \
    --strategy chunked --n-components 2 --n-clusters 15

# 5. Pool sintetica: celle finali di notebooks/notebook.ipynb
#    → data/processed/synthetic_workload_weighted.csv

# 6. Workload sintetico
poetry run python orchestrator.py --duration 3600 --threads 15 --think-time 0.01 \
    --manifest data/processed/synthetic_workload_weighted.csv --manifest-type synthetic \
    --hl-output data/raw/hl_report_synthetic.csv \
    --ll-global-output data/raw/ll_global_synthetic.csv \
    --ll-process-output data/raw/ll_process_synthetic.csv

# 7. Validazione
poetry run python -m analysis.extract_samples --input data/processed/ll_global_clean.csv \
    --output data/processed/samples_ll_global_real.csv --n-components 3 --n-clusters 15
poetry run python -m analysis.extract_samples --input data/processed/ll_global_synthetic_clean.csv \
    --output data/processed/samples_ll_global_synthetic.csv --n-components 3 --n-clusters 15
poetry run python -m analysis.hypothesis_tests \
    --real data/processed/samples_ll_global_real.csv \
    --synthetic data/processed/samples_ll_global_synthetic.csv \
    --output-dir analysis/plots/hypothesis_tests_ll_global
```

Per LL di processo si ripetono i passi 3–7 su `ll_process*.csv` (2 componenti).

## Note sulla pulizia dei dati

| Dataset | Righe (grezze → pulite) | Colonne rimosse | Trimming (inizio / fine) |
|---|---|---|---|
| LL globale | 3615 → 3560 | `mem_total` | 32 / 23 |
| LL processo | 3615 → 3560 | `pid`, `proc_io_*` | 32 / 23 |
| HL | 679046 → 679046 | `responseCode`, `success`, `URL` | — |
| LL' globale | 3615 → 3580 | `mem_total` | 11 / 24 |
| LL' processo | 3615 → 3586 | `pid`, `proc_io_*` | 9 / 20 |

- Le colonne di swap hanno bassa cardinalità ma un range significativo: vengono mantenute
- Le metriche di I/O disco/rete sono salvate come delta tra campioni successivi, non come
  contatori cumulativi (altrimenti la PCA catturerebbe solo lo scorrere del tempo)
- `proc_io_read_bytes` / `proc_io_write_bytes` non sono disponibili su macOS
- Gli outlier HL (~0.3%) sono distribuiti su tutta la run e non vengono rimossi
