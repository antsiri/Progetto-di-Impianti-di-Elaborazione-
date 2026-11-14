"""
 * author Antonio Sirignano
 * created on 29-10-2026-10h-36m
 * github: https://github.com/antsiri
 * copyright 2026

Loading and cleaning of the Excel workbook.
"""

import pandas as pd

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Dataset:
    """
    Cleaned content of one sheet.

    Attributes:
        name (str): sheet name.
        df (pandas.DataFrame): numeric data without missing values.
        x (str): independent variable (first column, time).
        ys (list[str]): dependent variables (remaining columns).
    """
    name: str
    df: pd.DataFrame
    x: str
    ys: list[str]


def clean_sheet(name: str, df: pd.DataFrame) -> Dataset:
    """
    Clean a raw sheet: drop empty and non-numeric columns and incomplete rows.

    Args:
        name (str): sheet name.
        df (pandas.DataFrame): raw sheet content.

    Returns:
        Dataset: cleaned data; the first column is used as x.
    """
    # Remove fully empty columns, then keep only numeric ones (drops text notes)
    df = df.dropna(axis=1, how='all').select_dtypes(include='number')

    # Uniform column names for the VM resource sheets
    if name.startswith('WMres'):
        df.columns = ['T(s)', 'Allocated Heap']

    # Drop rows with missing values
    df = df.dropna().reset_index(drop=True)
    return Dataset(name=name,
                   df=df,
                   x=df.columns[0],
                   ys=list(df.columns[1:])
                   )


def load_data(path_xls: str | Path) -> dict[str, Dataset]:
    """
    Read every sheet of the workbook and clean it.

    Args:
        path_xls (str | Path): Excel file.

    Returns:
        dict[str, Dataset]: sheet name -> cleaned dataset.
    """
    # sheet_name=None loads all sheets; calamine engine reads legacy .xls files
    sheets = pd.read_excel(path_xls, sheet_name=None, engine='calamine')
    return {name: clean_sheet(name, df) for name, df in sheets.items()}
