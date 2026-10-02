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

import argparse
from pathlib import Path

from analysis.clean import load_dataset, clean_report

def trim_edges(df, ramp_up: int, cooldown: int) -> list[int]:
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
    df = load_dataset(input_path)

    if drop_failed_requests and "success" in df.columns:
        before = len(df)
        df = df[df["success"] == True].reset_index(drop=True)
        dropped = before - len(df)
        if dropped:
            print(f"[INFO] Dropped {dropped} failed-request rows ({dropped/before*100:.4f}).")

    if dropna_columns:
        before = len(df)
        df = df.dropna(subset=dropna_columns).reset_index(drop=True)
        dropped = before - len(df)
        if dropped:
            print(f"[INFO] Dropped {dropped} rows with NaN in ({dropna_columns}).")
    

    rows_to_drop = trim_edges(df, ramp_up, cooldown) if (ramp_up or cooldown) else None

    cleaned = clean_report(df, columns_to_drop=columns_to_drop, rows_to_drop=rows_to_drop)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(output_path, index=False)
    print(f"Saved: {output_path} — shape {cleaned.shape} (from {df.shape})")


if __name__ == "__main__":
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