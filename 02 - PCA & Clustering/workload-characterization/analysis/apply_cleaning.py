"""
 * author Antonio Sirignano
 * created on 23-08-2026-14h-36m
 * github: https://github.com/antsiri
 * copyright 2026
"""

"""
 * author Antonio Sirignano
 * created on 22-08-2026-10h-40m
 * github: https://github.com/antsiri
 * copyright 2026
"""

from pathlib import Path
from analysis.clean import load_dataset, clean_report

RAMP_UP_ROWS = 32
COOLDOWN_ROWS = 23

def trim_edges(df, ramp_up, cooldown):
    return list(range(ramp_up)) + list(range(len(df) - cooldown, len(df)))

#LL Global
df = load_dataset(Path("data/raw/ll_global.csv"))
row_to_drop = trim_edges(df, RAMP_UP_ROWS, COOLDOWN_ROWS)
cleaned = clean_report(df, columns_to_drop=["mem_total"], rows_to_drop=row_to_drop)
cleaned.to_csv("data/processed/ll_global_clean.csv", index=False)

#LL process
df = load_dataset(Path("data/raw/ll_process.csv"))
row_to_drop = trim_edges(df, RAMP_UP_ROWS, COOLDOWN_ROWS)
cleaned = clean_report(df, columns_to_drop=["pid", "proc_io_read_bytes", "proc_io_write_bytes"], rows_to_drop=row_to_drop)
cleaned.to_csv("data/processed/ll_process_clean.csv", index=False)

#HL Report
df = load_dataset(Path("data/raw/hl_report.csv"))
cleaned = clean_report(df, columns_to_drop=["responseCode", "success", "URL"])
cleaned.to_csv("data/processed/hl_report_clean.csv", index=False)
