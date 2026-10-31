# DoE

Design of Experiments su un Web Server HTTP locale: effetto della dimensione della
pagina e dell'intensità del carico sul tempo di risposta, con modello lineare, ANOVA e
test non parametrici.

## Procedura

- **Risposta**: tempo di risposta medio (ms) su un test di 60 s
- **Fattori e livelli**:

| Fattore | Livelli |
|---|---|
| `PageType` | Low (20 KB), Mid-Low (184 KB), Mid (716 KB), Mid-High (2.13 MB), High (5.07 MB) |
| `Intensity` | 375 req/min (25% della usable capacity), 1125 req/min (75%) |

- **Piano**: full factorial 5 × 2 con 5 repliche → 50 prove

Analisi:

1. **Modello OLS** `ResponseTime ~ C(Intensity) * C(PageType)`: R², R² corretto, RMSE
2. **ANOVA** (tipo I) e **importanza dei fattori** come SS / SST
3. **Shapiro-Wilk** sui residui
4. **Kruskal-Wallis** su ciascun fattore, necessario perché i residui non sono normali e
   sono eteroschedastici
5. **Grafici diagnostici**: osservati vs previsti, QQ-plot dei residui, residui per `PageType`

Risultati principali:

- `PageType` spiega il 99.57% della varianza (p < 10⁻⁸)
- `Intensity` non è significativa nel range testato (Kruskal-Wallis p = 0.5474): entro la
  usable capacity il server lavora in zona stabile

## Struttura

```
.
├── pyproject.toml
├── main.py                      esecuzione completa (misure + analisi)
├── src/doe/
│   ├── Server/
│   │   ├── server_manager.py    genera le pagine in www_root/ e avvia HTTPServer su :8080
│   │   └── custom_handler.py    handler senza log delle richieste
│   ├── Benchmark/
│   │   └── benchmark_executor.py  invia richieste a ritmo costante e misura il tempo medio
│   └── DOE/
│       ├── runner.py            piano full factorial → measurements_doe.csv
│       └── analyzer.py          OLS, ANOVA, importanza, Shapiro-Wilk, Kruskal-Wallis, grafici
├── www_root/                    pagine HTML generate (Low … High)
├── measurements_doe.csv         misure raccolte (Intensity, PageType, ResponseTime)
└── Graphics_analysis.png        grafici diagnostici
```

## Uso

```bash
poetry install
poetry run python main.py
```

Se `measurements_doe.csv` esiste già, la fase di misura viene saltata e si esegue solo
l'analisi. Per ripetere le misure (circa 50 minuti) basta eliminare il file.
