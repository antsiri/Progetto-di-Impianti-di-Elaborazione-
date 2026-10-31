# FFDA

Field Failure Data Analysis sui log di errore di un cluster HPC (architettura Mercury):
coalescenza temporale degli eventi, tempi al guasto, reliability empirica, fit
parametrico e stima del MTTF.

## Procedura

1. **Ingestione e filtraggio**: i messaggi syslog vengono classificati in 6 categorie
   (DEV, MEM, I-O, NET, PRO, OTH) e salvati come `<timestamp> <nodo> <categoria> <messaggio>`
2. **Sensitività della CWIN**: numero di tuple al variare della coalescence window
   (10 … 800 s), scelta della finestra al gomito della curva → **CWIN = 200 s**
3. **Tupling**: gli eventi distanti meno della CWIN vengono raggruppati nella stessa tupla
4. **TTF**: tempi di inter-arrivo tra l'inizio di tuple consecutive
5. **Reliability empirica** R(t) = P(TTF > t)
6. **Fit non lineare** con modelli esponenziale, iper-esponenziale e di Weibull
   (usato l'iper-esponenziale), con R², SSE e test di Kolmogorov-Smirnov
7. **MTTF**: integrazione numerica della reliability stimata

Risultati sul log incluso (29 899 411 eventi):

| Tuple (CWIN = 200 s) | R² | SSE | KS p-value | MTTF |
|---|---|---|---|---|
| 183 242 | 0.99366 | 96.77 | 0.0000 | 7339.31 s (2.04 h) |

## Struttura

```
.
├── pyproject.toml
├── main.py                           pipeline completa
├── src/ffda/
│   ├── DataModels/datamodels.py      LogEntry, CoalescedTuple
│   ├── Monitor/monitor.py            LogFilterEngine (classificazione), monitor su file e syslog UDP
│   ├── Logger/
│   │   ├── baselogger.py             parser astratto con filtri per categoria/nodo
│   │   └── mercurylogger.py          parser del formato Mercury
│   ├── ColescenceEngine/colescence.py  tupling, inter-arrivi, analisi di sensitività
│   └── Reliability/
│       ├── reliability.py            reliability empirica, fit dei modelli, MTTF
│       └── visualizer.py             grafici di sensitività e di fit
├── mercury_syslog.log                log degli errori
├── plot_sensitivity.png              numero di tuple in funzione della CWIN
└── plot_reliability_fit.png          reliability empirica e fit iper-esponenziale
```

## Uso

```bash
poetry install
poetry run python main.py
```

Se `mercury_syslog.log` non esiste, `main.py` ne genera uno sintetico (200 000 episodi
di burst di errori con TTF iper-esponenziali); altrimenti usa quello presente.

## Note

- I grafici vengono salvati come `plot_sensitivity.png` e `plot_reliability_fit.png`,
  anche se `main.py` stampa `cwin_sensitivity.png` / `reliability_fit.png`
- `mercury_syslog.log` è escluso da git (`*.log` in `.gitignore`)
- Oltre al monitor su file (`FileTailMonitor`), è disponibile `SyslogServerMonitor`, che
  riceve syslog via UDP sulla porta 5140
