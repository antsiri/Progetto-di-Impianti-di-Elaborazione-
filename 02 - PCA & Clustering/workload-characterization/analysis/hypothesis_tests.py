"""
 * author Antonio Sirignano
 * created on 06-09-2026-19h-21m
 * github: https://github.com/antsiri
 * copyright 2026

Statistical validation of the synthetic workload against the real one.

Works on the per-cluster samples in PCA space (see ``extract_samples.py``):
    1. QQ-plots against the normal distribution;
    2. Kolmogorov-Smirnov normality test on each component;
    3. Wilcoxon rank-sum test (synthetic vs real) on each component.
"""

import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path
from scipy import stats


def load_cluster_samples(csv_path: Path) -> np.ndarray:
    """
    Load the PC coordinates of the cluster samples.

    Args:
        csv_path (Path): CSV produced by ``extract_samples.py``.

    Returns:
        np.ndarray: matrix ``(n_samples, n_components)`` (``cluster`` column removed).
    """
    df = pd.read_csv(csv_path)
    return df.select_dtypes(include="number").drop(columns=["cluster"], errors="ignore").values


def qq_plot_comparison(real: np.ndarray, synthetic: np.ndarray, output_path: Path):
    """
    Save a grid of normal QQ-plots: first row real, second row synthetic,
    one column per principal component.

    Args:
        real (np.ndarray): real samples.
        synthetic (np.ndarray): synthetic samples.
        output_path (Path): image file to write.
    """
    n_components = real.shape[1]
    fig, axes = plt.subplots(2, n_components, figsize=(4*n_components, 8))
    # With a single component subplots returns a 1-D array: force 2-D indexing
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
    """
    Kolmogorov-Smirnov normality test on every column of ``data``.

    Each column is standardised and compared with the standard normal.

    Args:
        data (np.ndarray): samples ``(n_samples, n_components)``.
        alpha (float): significance level.

    Returns:
        pandas.DataFrame: statistic, p-value and ``reject_normality`` flag per component.
    """
    results = []
    for i in range(data.shape[1]):
        # Standardise so the sample can be compared with N(0, 1)
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
    """
    Wilcoxon rank-sum test (non-parametric) between synthetic and real
    samples, component by component. H0: the two samples come from the
    same distribution (same median).

    Args:
        real (np.ndarray): real samples.
        synthetic (np.ndarray): synthetic samples.
        alpha (float): significance level.

    Returns:
        pandas.DataFrame: statistic, p-value and ``reject_same_median`` flag per component.

    Raises:
        ValueError: if the number of components differs.
    """
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
    """
    Run the whole validation pipeline and save plots and result tables.

    Args:
        real_csv (Path): samples of the real workload.
        synthetic_csv (Path): samples of the synthetic workload.
        output_dir (Path): folder for the QQ-plot and the CSV results.
        alpha (float): significance level for all tests.
    """
    real = load_cluster_samples(real_csv)
    synthetic = load_cluster_samples(synthetic_csv)

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Visual normality check
    print("=== QQ-plot ===")
    qq_plot_comparison(real, synthetic, output_dir / "qq_plot_comparison.png")
    print(f"File saved in {output_dir / 'qq_plot_comparison.png'}")

    # 2. Formal normality test on both datasets
    print("=== Kolmogorov-Smirnov - Real ===")
    ks_real = kolmogorov_smirnov_test(real, alpha)
    print(ks_real.to_string(index=False))

    print("=== Kolmogorov-Smirnov - Synthetic ===")
    ks_synthetic = kolmogorov_smirnov_test(real, alpha)
    print(ks_synthetic.to_string(index=False))

    # Choice of the comparison test depends on normality
    all_normal = not (ks_real["reject_normality"].any() or ks_synthetic["reject_normality"].any())
    if all_normal:
        print("\n[INFO] All data seems normal: it can be used t-test instead Wilcoxon.")
    else:
        print("\n[INFO] Almost a compontent is not normal: using a no-parametric test (Wilcoxon).")

    # 3. Non-parametric comparison synthetic vs real
    print("\n=== Wilcoxon ranksum (Synthetic vs Real) ===")
    wilcoxon_results = wilcoxon_ranksum_test(real, synthetic, alpha)
    print(wilcoxon_results.to_string(index=False))

    print("\n=== Wilcoxon ranksum (Synthetic vs Real) ===")
    wilcoxon_results = wilcoxon_ranksum_test(real, synthetic, alpha)
    print(wilcoxon_results.to_string(index=False))

    # Persist all result tables
    wilcoxon_results.to_csv(output_dir / "wilcoxon_results.csv", index=False)
    ks_real.to_csv(output_dir / "ks_real.csv", index=False)
    ks_synthetic.to_csv(output_dir / "ks_synthetic.csv", index=False)

    # Final verdict: number of components where H0 is rejected
    n_rejected = wilcoxon_results["reject_same_median"].sum()
    print(f"\n=== Conclusione ===")
    if n_rejected == 0:
        print("No component ejected H0: synthetic workload is equal to real one statistically.")
    else:
        print(f"{n_rejected}/{len(wilcoxon_results)} components ejecte H0: significant differences revealed.")


if __name__ == "__main__":
    # Command-line interface
    parser = argparse.ArgumentParser(description="Statistical validation: real vs synthetic workload (LL)")
    parser.add_argument("--real", type=Path, required=True)
    parser.add_argument("--synthetic", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("analysis/plots/hypothesis_tests"))
    parser.add_argument("--alpha", type=float, default=0.05)

    args = parser.parse_args()
    run_full_validation(args.real, args.synthetic, args.output_dir, args.alpha)
