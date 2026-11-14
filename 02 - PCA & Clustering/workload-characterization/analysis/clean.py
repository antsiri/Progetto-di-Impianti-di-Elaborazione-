"""
 * author Antonio Sirignano
 * created on 21-08-2026-11h-58m
 * github: https://github.com/antsiri
 * copyright 2026

Dataset inspection utilities for the PCA / clustering pipeline.

Prints summary statistics, flags low-variance columns and outlier rows and
saves a histogram + boxplot for every numeric column, so that the cleaning
decisions can be taken before running ``analysis/apply_cleaning.py``.
"""

import argparse
import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path


def load_dataset(csv_path: Path) -> pd.DataFrame:
    """
    Load a CSV file and print its shape.

    Args:
        csv_path (Path): CSV file to load.

    Returns:
        pandas.DataFrame: loaded dataset.
    """
    df = pd.read_csv(csv_path)
    print(f"Loaded {csv_path.name}: {df.shape[0]} rows, {df.shape[1]} columns.")
    return df


def summarize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Descriptive statistics of every column, plus number and percentage of
    unique values.

    Args:
        df (pandas.DataFrame): dataset to describe.

    Returns:
        pandas.DataFrame: one row per column of ``df``.
    """
    summary = df.describe(include='all').T
    summary['nuinque'] = df.nunique()
    summary['pct_unique'] = (summary['nuinque'] / len(df) * 100).round(2)
    return summary


def plot_distribution(df: pd.DataFrame, output_dir: Path, cols_per_fig : int = 3):
    """
    Save a histogram and a boxplot for each numeric column.

    Args:
        df (pandas.DataFrame): dataset to plot.
        output_dir (Path): folder where one ``<column>.png`` per column is saved.
        cols_per_fig (int): currently unused.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    numeric_cols = df.select_dtypes(include='number').columns

    for col in numeric_cols:
        # Left: histogram, right: boxplot (useful to spot outliers)
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        df[col].hist(bins=30, ax=axes[0], color='#8fae8f')
        axes[0].set_title(f"{col} - distribution")

        axes[1].boxplot(df[col].dropna())
        axes[1].set_title(f"{col} - boxplot")

        fig.tight_layout()
        fig.savefig(output_dir / f"{col}.png")
        # Close the figure to free memory inside the loop
        plt.close(fig)

    print(f"Saved {len(numeric_cols)} distribution plots to {output_dir}")


def find_low_variance_columns(df: pd.DataFrame, unique_ratio_threshold: float = 0.01) -> list:
    """
    Flag numeric columns with very few distinct values (little information).

    Args:
        df (pandas.DataFrame): dataset to inspect.
        unique_ratio_threshold (float): a column is flagged when
            ``n_unique / n_rows`` is below this value.

    Returns:
        list[tuple[str, int, float]]: ``(column, n_unique, unique_percentage)``.
    """
    numeric_cols = df.select_dtypes(include='number').columns
    flagged = []

    for col in numeric_cols:
        ratio = df[col].nunique() / len(df)
        if ratio < unique_ratio_threshold:
            flagged.append((col, df[col].nunique(), round(ratio * 100, 4)))
    return flagged


def find_outlier_rows(df: pd.DataFrame, z_threshold: float = 4.0) -> pd.DataFrame:
    """
    Return the rows where at least one numeric value has ``|z-score| > z_threshold``.

    Args:
        df (pandas.DataFrame): dataset to inspect.
        z_threshold (float): z-score threshold.

    Returns:
        pandas.DataFrame: the outlier rows.
    """
    numeric_df = df.select_dtypes(include='number')
    # Standardise each column: z = (x - mean) / std
    z_score = (numeric_df - numeric_df.mean()) / numeric_df.std()
    mask = (z_score.abs() > z_threshold).any(axis=1)
    return df[mask]


def clean_report(df: pd.DataFrame, columns_to_drop: list, rows_to_drop: list = None) -> pd.DataFrame:
    """
    Drop the given columns and rows and reset the index.

    Args:
        df (pandas.DataFrame): dataset to clean.
        columns_to_drop (list): column names to remove (missing ones are ignored).
        rows_to_drop (list | None): row indices to remove.

    Returns:
        pandas.DataFrame: cleaned dataset.
    """
    cleaned = df.drop(columns=columns_to_drop, errors='ignore')
    if rows_to_drop:
        cleaned = cleaned.drop(index=rows_to_drop, errors='ignore')
    return cleaned.reset_index(drop=True)


if __name__ == "__main__":
    # Command-line interface
    parser = argparse.ArgumentParser(description='Dataset inspection for PCA/Clustering pipeline')
    parser.add_argument("--input", type=Path, required=True, help="CSV path (hl_report / ll_glovbal / ll_process)")
    parser.add_argument("--plots-dir", type=Path, default=Path("analysis/plots"))
    parser.add_argument("--variance-threshold", type=float, default=0.01)
    parser.add_argument("--zscore-threshold", type=float, default=4.0)

    args = parser.parse_args()

    df = load_dataset(args.input)

    print("\n=== Summary Statistics ===")
    print(summarize_columns(df))

    print("\n=== Low-Variance columns (candidate for removal) ===")
    low_var = find_low_variance_columns(df, args.variance_threshold)
    if low_var:
        for col, nunique, pct in low_var:
            print(f"\t{col}: {nunique} unique values ({pct}%)")
    else:
        print("\tNone flagged.")

    print("\n=== Outliers rows (candidate for removal) ===")
    outliers = find_outlier_rows(df, args.zscore_threshold)
    print(f"\t{len(outliers)} rows flagged")
    if not outliers.empty:
        print(outliers.head())

    # Plots are saved in a sub-folder named after the input file
    plot_distribution(df, args.plots_dir / args.input.stem)
    print(f"\nInspect plots in {args.plots_dir / args.input.stem} before deciding cleaning actions.")
