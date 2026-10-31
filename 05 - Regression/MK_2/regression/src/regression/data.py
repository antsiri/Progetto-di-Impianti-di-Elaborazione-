"""
 * author Antonio Sirignano
 * created on 29-10-2026-10h-36m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import pandas as pd

from dataclasses import dataclass
from pathlib import Path

@dataclass
class Dataset:
    name: str
    df: pd.DataFrame
    x: str
    ys: list[str]

def clean_sheet(name: str, df: pd.DataFrame) -> Dataset:
    df = df.dropna(axis=1, how='all').select_dtypes(include='number')

    if name.startswith('WMres'):
        df.columns = ['T(s)', 'Allocated Heap']

    df = df.dropna().reset_index(drop=True)
    return Dataset(name=name,
                   df=df,
                   x=df.columns[0],
                   ys=list(df.columns[1:])
                   )

def load_data(path_xls: str | Path) -> dict[str, Dataset]:
    sheets = pd.read_excel(path_xls, sheet_name=None, engine='calamine')
    return {name: clean_sheet(name, df) for name, df in sheets.items()}