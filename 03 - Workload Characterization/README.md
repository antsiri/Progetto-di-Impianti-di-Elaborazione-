# Workload Characterization

Caratterizzazione statistica del carico LL di un Web Server sollecitato con Locust,
modellazione della distribuzione dei context switch e costruzione di un generatore
sintetico multi-processo, validato contro il carico reale.

## Procedura

1. **Carico reale**: Locust richiede 9 file statici (small / medium / large, pesi 50/35/15)
   a 21.6 req/s per utente; il monitor `psutil` registra ogni secondo le metriche in
   formato vmstat (`report_LL_real.txt`)
2. **Pre-processing**: rimozione delle intestazioni ripetute, normalizzazione dei
   separatori decimali, cast a `float64` ed eliminazione dei `NaN`
3. **Caratterizzazione descrittiva** di `cs`, `us`, `sy`, `free`: media, deviazione
   standard, minimo, mediana, massimo
4. **Modellazione**: matrice di correlazione di Pearson, autocorrelazione dei `cs`,
   fitting di distribuzioni candidate e test di **Kolmogorov-Smirnov** a un campione
   → miglior modello: **Gamma** (D = 0.0435, p = 0.0648)
5. **Generatore sintetico**: N coppie di processi che si scambiano un byte via pipe
   (ping-pong IPC, genera context switch senza il limite del GIL) più un micro-ciclo di
   calcolo per la CPU user; ogni secondo il target di `cs` è estratto dalla Gamma stimata
   e distribuito ai worker tramite `mp.Value` / `mp.Event`
6. **Validazione**: medie, errore relativo e test di KS a due campioni reale vs sintetico

| Metrica | Media reale | Media sintetica | Errore rel. | KS D |
|---|---|---|---|---|
| `cs` | 26057.26 | 33109.67 | 27.07% | 0.4078 |
| `us` [%] | 10.42 | 3.34 | 67.93% | 0.9710 |
| `sy` [%] | 5.81 | 1.60 | 72.49% | 0.9754 |
| `free` | 88250.34 | 124865.98 | 41.49% | 0.4123 |

Il generatore riproduce l'ordine di grandezza dei context switch ma non l'occupazione
della CPU: tutti i test KS rigettano H₀ (p < 0.0001). Possibili sviluppi: riscrittura in C
con pthreads e calibrazione dinamica del carico CPU.

## Struttura

```
.
├── pyproject.toml
├── data/                         file statici serviti al carico reale (small/medium/large)
├── LoadGenerator/locustfile.py   utente Locust con richieste pesate per categoria
├── Monitor/monitor_ll.py         monitor LL psutil in formato vmstat
├── Synthetic/synthetic_generator.py  generatore sintetico multi-processo (Gamma + pipe IPC)
├── Analysis/
│   ├── report_analysis.py        statistiche descrittive → workload_profile.png
│   ├── statistical_analysis.py   correlazioni, autocorrelazione, GoF → statistical_distributions.png
│   └── validate_workload.py      reale vs sintetico → workload_validation_comparison.png
├── report_LL_real.txt            tracciato LL del carico reale
└── report_LL_synthetic.txt       tracciato LL del carico sintetico
```

## Uso

```bash
poetry install

# Carico reale: server statico su data/ + Locust + monitor
python3 -m http.server 8000 --directory data
poetry run locust -f LoadGenerator/locustfile.py --host http://127.0.0.1:8000
poetry run python Monitor/monitor_ll.py

# Carico sintetico (900 s, legge i parametri Gamma da report_LL_real.txt)
poetry run python Synthetic/synthetic_generator.py
poetry run python Monitor/monitor_ll.py     # in parallelo

# Analisi
poetry run python Analysis/report_analysis.py
poetry run python Analysis/statistical_analysis.py
poetry run python Analysis/validate_workload.py
```

## Note

- `monitor_ll.py` scrive su `report_LL_synthetic.txt` per 900 s: per il carico reale
  va cambiato `OUTPUT_FILE` (e `DURATION` se serve)
- Le colonne non disponibili tramite `psutil` su macOS (`r`, `b`, `si`, `so`, `bi`,
  `bo`, `in`, `st`) sono scritte a 0 per mantenere il formato vmstat
- Gli script in `Analysis/` usano percorsi assoluti verso i report: vanno aggiornati se
  il progetto viene spostato
