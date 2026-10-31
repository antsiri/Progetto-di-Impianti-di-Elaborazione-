# Benchmark

Confronto statisticamente rigoroso delle prestazioni di due macchine (laptop e desktop)
con un benchmark di simulazione N-Body (complessità O(N²)), compilato JIT con Numba.

## Procedura

1. **Benchmark**: simulazione gravitazionale di N corpi per 5 step, kernel `@njit`
   parallelo; il JIT viene riscaldato prima della misura e ogni run è un processo separato
2. **Raccolta**: 31 run per ogni N e per ogni macchina, tempi in ms salvati in
   `benchmark_<device>_<N>.txt`
3. **Statistiche descrittive**: media, deviazione standard, errore standard, IC al 95%,
   quartili
4. **Dimensione campionaria teorica** per errori del 5%, 8% e 10% sulla media
5. **Normalità**: test di Shapiro-Wilk
6. **Omoschedasticità**: test di Brown-Forsythe (Levene sulla mediana)
7. **Confronto**: Welch t-test e Wilcoxon rank-sum

| N | Media laptop | Media desktop | Wilcoxon p | Più veloce |
|---|---|---|---|---|
| 10 000 | 210.84 ms | 205.45 ms | 1.93·10⁻⁵ | Desktop |
| 100 000 | 23 407.46 ms | 24 443.98 ms | 1.69·10⁻⁷ | Laptop |

## Struttura

```
.
├── pyproject.toml
├── src/benchmark/
│   ├── Nbody/nbody_simulator.py      kernel N-Body (Numba) e misura di una singola run
│   ├── Runner/benchmark_runner.py    esegue le 31 run per ogni N e salva i tempi
│   └── Analysis/analysis.py          statistiche, test e grafici di confronto
├── benchmark_<laptop|desktop>_<N>.txt  tempi misurati (N = 10000, 100000, 1000000)
├── comparison_<N>.png                boxplot e medie con IC al 95%
└── llvmlite-0.45.1-...-x86_64.whl    wheel di llvmlite per macOS Intel
```

## Uso

```bash
poetry install

# Raccolta dati, da eseguire su ciascuna macchina
poetry run python src/benchmark/Runner/benchmark_runner.py laptop
poetry run python src/benchmark/Runner/benchmark_runner.py desktop

# Analisi (legge i file .txt dalla cartella corrente)
poetry run python src/benchmark/Analysis/analysis.py
```

## Note

- `benchmark_runner.py` lancia `nbody_simulator.py` tramite un percorso assoluto che va
  adattato alla posizione del progetto
- Il runner usa di default N = 10000, 100000, 500000; l'analisi considera solo
  N = 10000 e 100000
- Numba e llvmlite sono fissati a versioni compatibili con `numpy < 2.4`; su macOS Intel
  può servire installare il wheel di llvmlite incluso
