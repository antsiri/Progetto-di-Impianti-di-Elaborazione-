"""
 * author Antonio Sirignano
 * created on 06-09-2026-19h-21m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path
from scipy import stats

def load_cluster_samples(csv_path: Path) -> np.ndarray:
    df = pd.read_csv(csv_path)
    return df.select_dtypes(include="number").drop(columns=["cluster"], errors="ignore").values

def qq_plot_comparison(real: np.ndarray, synthetic: np.ndarray, output_path: Path):
    n_components = real.shape[1]
    fig, axes = plt.subplots(2, n_components, figsize=(4*n_components, 8))
    if n_components == 1:
        axes = axes.reshape(2, 1)

    for i in range(n_components):
        stats.probplot(real[:, i], dist="norm", plot=axes[0, i])
        axes[0, i].set_title(f"Real - PC{i+1}")

        stats.probplot(synthetic[:, i], dist="norm", plot=axes[1, i])
        axes[1, i].set_title(f"Synthetic - PC{i+1}")

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path)
    plt.close(fig)

def kolmogorov_smirnov_test(data: np.ndarray, alpha: float = 0.05) -> pd.DataFrame:
    results = []
    for i in range(data.shape[1]):
        standardized = (data[:, i] - data[:, i].mean()) / data[:, i].std()
        statistic, p_value = stats.kstest(standardized, "norm")
        results.append({
            "component": f"PC{i+1}",
            "ks_statistic": round(statistic, 4),
            "p_value": round(p_value, 4),
            "reject_normality": p_value < alpha    
        })

    return pd.DataFrame(results)

def wilcoxon_ranksum_test(real: np.ndarray, synthetic: np.ndarray, alpha: float = 0.05) -> pd.DataFrame:
    if real.shape[1] != synthetic.shape[1]:
        raise ValueError(f"Components Mismatch: real={real.shape[1]}, synthetic={synthetic.shape[1]}")

    results = []
    for i in range(real.shape[1]):
        statistic, p_value = stats.ranksums(synthetic[:, i], real[:, i])
        results.append({
            "component": f"PC{i+1}",
            "statistic": round(statistic, 4),
            "p_value": round(p_value, 4),
            "reject_same_median": p_value < alpha,      
        })

    return pd.DataFrame(results)

def run_full_validation(real_csv: Path, synthetic_csv: Path, output_dir: Path, alpha: float = 0.05):
    real = load_cluster_samples(real_csv)
    synthetic = load_cluster_samples(synthetic_csv)

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=== QQ-plot ===")
    qq_plot_comparison(real, synthetic, output_dir / "qq_plot_comparison.png")
    print(f"File saved in {output_dir / 'qq_plot_comparison.png'}")

    print("=== Kolmogorov-Smirnov - Real ===")
    ks_real = kolmogorov_smirnov_test(real, alpha)
    print(ks_real.to_string(index=False))

    print("=== Kolmogorov-Smirnov - Synthetic ===")
    ks_synthetic = kolmogorov_smirnov_test(real, alpha)
    print(ks_synthetic.to_string(index=False))

    all_normal = not (ks_real["reject_normality"].any() or ks_synthetic["reject_normality"].any())
    if all_normal:
        print("\n[INFO] All data seems normal: it can be used t-test instead Wilcoxon.")
    else:
        print("\n[INFO] Almost a compontent is not normal: using a no-parametric test (Wilcoxon).")

    print("\n=== Wilcoxon ranksum (Synthetic vs Real) ===")
    wilcoxon_results = wilcoxon_ranksum_test(real, synthetic, alpha)
    print(wilcoxon_results.to_string(index=False))

    print("\n=== Wilcoxon ranksum (Synthetic vs Real) ===")
    wilcoxon_results = wilcoxon_ranksum_test(real, synthetic, alpha)
    print(wilcoxon_results.to_string(index=False))

    wilcoxon_results.to_csv(output_dir / "wilcoxon_results.csv", index=False)
    ks_real.to_csv(output_dir / "ks_real.csv", index=False)
    ks_synthetic.to_csv(output_dir / "ks_synthetic.csv", index=False)

    n_rejected = wilcoxon_results["reject_same_median"].sum()
    print(f"\n=== Conclusione ===")
    if n_rejected == 0:
        print("No component ejected H0: synthetic workload is equal to real one statistically.")
    else:
        print(f"{n_rejected}/{len(wilcoxon_results)} components ejecte H0: significant differences revealed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Statistical validation: real vs synthetic workload (LL)")
    parser.add_argument("--real", type=Path, required=True)
    parser.add_argument("--synthetic", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("analysis/plots/hypothesis_tests"))
    parser.add_argument("--alpha", type=float, default=0.05)

    args = parser.parse_args()
    run_full_validation(args.real, args.synthetic, args.output_dir, args.alpha)
 