"""
 * author Antonio Sirignano
 * created on 23-08-2026-14h-36m
 * github: https://github.com/antsiri
 * copyright 2026

Apply the cleaning decisions (taken after inspecting the data with
``analysis/clean.py``) to a raw dataset and save the cleaned CSV.

Supported actions: drop failed requests, drop rows with NaN in selected
columns, trim ramp-up / cool-down rows and drop useless columns.
"""

"""
 * author Antonio Sirignano
 * created on 22-08-2026-10h-40m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import argparse
from pathlib import Path

from analysis.clean import load_dataset, clean_report


def trim_edges(df, ramp_up: int, cooldown: int) -> list[int]:
    """
    Return the row indices belonging to the ramp-up and cool-down phases.

    Args:
        df (pandas.DataFrame): dataset whose length is used.
        ramp_up (int): number of initial rows to discard.
        cooldown (int): number of final rows to discard.

    Returns:
        list[int]: indices of the first ``ramp_up`` and last ``cooldown`` rows.
    """
    return list(range(ramp_up)) + list(range(len(df) - cooldown, len(df)))


def apply_cleaning(
    input_path: Path,
    output_path: Path,
    columns_to_drop: list[str],
    ramp_up: int = 0,
    cooldown: int = 0,
    drop_failed_requests: bool = False,
    dropna_columns: list[str] = None,
):
    """
    Load a raw CSV, apply the requested cleaning steps and save the result.

    Args:
        input_path (Path): raw CSV to clean.
        output_path (Path): destination of the cleaned CSV (folders are created).
        columns_to_drop (list[str]): columns to remove.
        ramp_up (int): initial rows to discard (transient phase).
        cooldown (int): final rows to discard (transient phase).
        drop_failed_requests (bool): if True keep only rows with ``success == True``.
        dropna_columns (list[str] | None): columns on which rows with NaN are dropped.
    """
    df = load_dataset(input_path)

    # Remove failed requests (only if the 'success' column exists)
    if drop_failed_requests and "success" in df.columns:
        before = len(df)
        df = df[df["success"] == True].reset_index(drop=True)
        dropped = before - len(df)
        if dropped:
            print(f"[INFO] Dropped {dropped} failed-request rows ({dropped/before*100:.4f}).")

    # Extra safety: remove rows with missing values in the given columns
    if dropna_columns:
        before = len(df)
        df = df.dropna(subset=dropna_columns).reset_index(drop=True)
        dropped = before - len(df)
        if dropped:
            print(f"[INFO] Dropped {dropped} rows with NaN in ({dropna_columns}).")


    # Rows of the transient phases (None if no trimming was requested)
    rows_to_drop = trim_edges(df, ramp_up, cooldown) if (ramp_up or cooldown) else None

    cleaned = clean_report(df, columns_to_drop=columns_to_drop, rows_to_drop=rows_to_drop)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(output_path, index=False)
    print(f"Saved: {output_path} — shape {cleaned.shape} (from {df.shape})")


if __name__ == "__main__":
    # Command-line interface
    parser = argparse.ArgumentParser(description="Apply cleaning decisions to a raw dataset")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--drop-columns", nargs="*", default=[])
    parser.add_argument("--ramp-up", type=int, default=0, help="Starting rows to drop.")
    parser.add_argument("--cooldown", type=int, default=0, help="Ending row to drop.")
    parser.add_argument("--drop-failed-requests", action="store_true", help="Drops rows with 'success=False' before drops 'success' column")
    parser.add_argument("--dropna-columns", nargs="*", default=None, help="Columns on which apply dropna as extra security")

    args = parser.parse_args()
    apply_cleaning(
        input_path=args.input,
        output_path=args.output,
        columns_to_drop=args.drop_columns,
        ramp_up=args.ramp_up,
        cooldown=args.cooldown,
        drop_failed_requests=args.drop_failed_requests,
        dropna_columns=args.dropna_columns,
    )
