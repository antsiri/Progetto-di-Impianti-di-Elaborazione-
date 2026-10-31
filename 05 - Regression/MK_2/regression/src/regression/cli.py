"""
 * author Antonio Sirignano
 * created on 31-10-2026-08h-58m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import argparse
from pathlib import Path

import pandas as pd

from .analysis import analyze
from .config import DEFAULT_DATA, DEFAULT_OUTPUT
from .data import load_data
from .failure import failure_prediction
from .plots import pair_plot

def execute(path_xls: Path, output: Path, plots: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    output.mkdir(parents=True, exist_ok=True)
    results, failure = [], []
    
    for sheet, ds in load_data(path_xls).items():
        print(f'\n=== {sheet} (n = {len(ds.df)}), X = {ds.x} ===')
        for y in ds.ys:
            analysis = analyze(sheet, ds.df, ds.x, y)
            r = analysis.values
            results.append(r)
            if plots:
                pair_plot(ds.df, analysis, output / 'figure')
            
            row = (f'   {y:<24} R2={r['R2']:.4f} KSL_D={r['KSL_D']:.4f} tau={r['kendall_tau']:+.4f} p={r['kendall_p']:.4f}')
            
            if r['trend']:
                row += (f'  | Theil-Sen m={r['ts_slope']:.3f} q={r['ts_intercept']:.3f} IC=[{r['ts_ic_inf']:.3f}, {r['ts_ic_sup']:.3f}]')
            else:
                row += '    | no trend'
            
            print(row)

            if sheet.startswith('VMRes') and r['trend']:
                failure.append(failure_prediction(r))

    tab = pd.DataFrame(results)
    tab.to_csv(output / 'results.csv', index=False)

    fp = pd.DataFrame(failure)
    if not fp.empty:
        fp.to_csv(output / 'failure_prediction.csv', index=False)
        print(' Failure Prediction (heap = 1GB) ===')
        for _, f in fp.iterrows():
            print(f"  {f['sheet']}: T = {f['T_failure_years']:.1f} years (IC: {f['T_min_years']:.1f} - {f['T_max_years']:.1f} years)")
        best = fp.loc[fp["T_min_years"].idxmax(), "sheet"]
        print(f'    VM that maximize the failure time (IC worst case): {best}')

    print(f'\nSaved results in {output.resolve()}')
    return tab, fp

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description='HomeWork Regression')
    parser.add_argument('--data', type=Path, default=DEFAULT_DATA, help='Input file .xls')
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT, help='Output folder')
    parser.add_argument('--no-plots', action='store_true', help='no plots generation')
    args = parser.parse_args(argv)

    execute(args.data, args.output, plots=not args.no_plots)

if __name__ == "__main__":
    main()