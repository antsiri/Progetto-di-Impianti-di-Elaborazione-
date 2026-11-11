# Impianti di Elaborazione

Raccolta degli elaborati del corso di Impianti di Elaborazione: analisi delle prestazioni
e dell'affidabilità di sistemi di elaborazione, dalla misura sul campo alla modellazione
statistica. Ogni cartella è un progetto autonomo, con il proprio `pyproject.toml` e un
README che ne descrive procedura, struttura e risultati.

## Esercizi

| # | Cartella | Argomento |
|---|---|---|
| 1 | [`01 - Capacity Test`](<01 - Capacity Test>) | Capacity test di un Web Server con JMeter (3 iterazioni da 300 s) e monitoraggio LL con `vmstat`; analisi di throughput, tempi di risposta e colli di bottiglia |
| 2 | [`02 - PCA & Clustering`](<02 - PCA & Clustering>) | Workload characterization con PCA e clustering gerarchico, costruzione e validazione di un workload sintetico |
| 3 | [`03 - Workload Characterization`](<03 - Workload Characterization>) | Caratterizzazione statistica del carico LL, fitting di distribuzioni e generatore sintetico multi-processo |
| 4 | [`04-DoE`](04-DoE) | Design of Experiments full factorial 5 × 2 su un Web Server: OLS, ANOVA, Kruskal-Wallis |
| 5 | [`05 - Regression`](<05 - Regression>) | Analisi di regressione, trend (Kendall, Theil-Sen) e failure prediction |
| 6 | [`06 - Benchmark`](<06 - Benchmark>) | Confronto tra due macchine con un benchmark N-Body (Numba) e test statistici |
| 7 | [`07 - FFDA`](<07 - FFDA>) | Field Failure Data Analysis su log HPC: tupling, reliability empirica e MTTF |

La relazione completa è in [`Docs.pdf`](Docs.pdf).

## Requisiti

- Python ≥ 3.13
- [Poetry](https://python-poetry.org/) ≥ 2.0
- Apache JMeter (solo per l'esercizio 1)

## Uso

Ogni esercizio si esegue dalla propria cartella:

```bash
cd "<cartella dell'esercizio>"
poetry install
```

I comandi specifici sono riportati nel README di ciascun esercizio.

## Licenza

Distribuito con licenza MIT, vedi [`LICENSE`](LICENSE). I componenti di terze parti
inclusi (ad esempio i report HTML generati da JMeter in `01 - Capacity Test/report_html_iter_*`)
restano soggetti alle rispettive licenze.
