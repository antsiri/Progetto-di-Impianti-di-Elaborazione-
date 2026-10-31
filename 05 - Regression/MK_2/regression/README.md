# HomeWork Regression

Riproduzione in Python dell'analisi di regressione della tesina di riferimento
(originariamente svolta in JMP + SciPy) sui fogli di `data/HomeWork_Regression.xls`.

## Procedura

Per ogni foglio e per ogni variabile di risposta Y rispetto al tempo X:

1. **Stima lineare (OLS)**: R², R² corretto, RMSE, ANOVA, stime dei parametri
2. **Normalità dei residui**: istogramma, QQ-plot e **test di KSL** (Lilliefors)
3. **Trend**: **τ di Kendall** tra X e Y (il "Mann-Kendall" della tesina, come calcolato da JMP)
4. Se p < 0.05: **stimatore di Theil-Sen** con IC al 95%
5. Solo VMres1-3: **failure prediction**, tempo per saturare 1 GB di heap

| Foglio | X | Y |
|---|---|---|
| EXP1, EXP2 | `observation` | nmail, byte rec, byte sent |
| os1 / os2 / os3 | `TIME` | VmSize, VmData, RSS, byte letti/scritti |
| VMres1-3 | `T(s)` | Allocated Heap |

## Struttura

```
.
├── data/HomeWork_Regression.xls
└── regression/
    ├── pyproject.toml
    ├── src/regression/
    │   ├── config.py      costanti (ALPHA, limite heap) e percorsi di default
    │   ├── data.py        caricamento e pulizia dei fogli
    │   ├── analysis.py    OLS, KSL, Kendall, Theil-Sen
    │   ├── failure.py     failure prediction
    │   ├── plots.py       grafici (scatter + rette, istogramma residui, QQ-plot)
    │   └── cli.py         esecuzione completa e salvataggio risultati
    └── tests/
        ├── test_unit.py   test su dati sintetici
        └── test_tesina.py confronto con i valori della tesina
```

## Uso

Dalla cartella `regression/`:

```bash
poetry install                   # crea il venv e installa dipendenze + pytest
poetry run regression            # esegue l'analisi → output/
poetry run pytest                # esegue i test
```

Opzioni: `--data FILE.xls`, `--output CARTELLA`, `--no-plots`.

Output in `regression/output/`:

- `risultati.csv`: una riga per ogni coppia (foglio, variabile) con tutti i valori
- `failure_prediction.csv`: tempi di failure per VMres1-3
- `figure/<foglio>_<variabile>.png`: un grafico per ogni coppia

## Note sulla pulizia dei dati

- **os2**: colonne vuote e una cella di testo ("NO MEMORY DEPLETION!!!") eliminate
- **os3**: 3 righe finali senza `TIME` eliminate
- **VMres**: nomi delle colonne uniformati (`T(s)`, `Allocated Heap`)
- **EXP1**: `observation` riparte da 0 a metà file (due run concatenati). Per questo si usa
  il τ di Kendall tra X e Y e non `pymannkendall`, che assume righe in ordine temporale.
