"""
 * author Antonio Sirignano
 * created on 10-10-2026-17h-24m
 * github: https://github.com/antsiri
 * copyright 2026
"""

# analysis.py
import numpy as np
import pandas as pd
import scipy.stats as stats
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Tuple


class SampleDataset:
    """Classe che rappresenta e analizza un singolo campione di misurazioni."""

    def __init__(self, device: str, n_bodies: int, filepath: str = None):
        self.device = device
        self.n_bodies = n_bodies
        self.filepath = filepath or f"benchmark_{device}_{n_bodies}.txt"
        self.data = self._load_data()

    def _load_data(self) -> np.ndarray:
        return np.loadtxt(self.filepath)

    @property
    def n(self) -> int:
        return len(self.data)

    @property
    def mean(self) -> float:
        return float(np.mean(self.data))

    @property
    def std(self) -> float:
        return float(np.std(self.data, ddof=1))

    @property
    def se(self) -> float:
        return self.std / np.sqrt(self.n)

    @property
    def confidence_interval_95(self) -> Tuple[float, float]:
        return stats.t.interval(0.95, df=self.n - 1, loc=self.mean, scale=self.se)

    def get_summary_stats(self) -> Dict[str, float]:
        ci_low, ci_high = self.confidence_interval_95
        quantiles = np.percentile(self.data, [0, 25, 50, 75, 100])
        return {
            'N': self.n,
            'Mean': self.mean,
            'Std Dev': self.std,
            'Error Std': self.se,
            'CI 95% Inf': ci_low,
            'CI 95% Sup': ci_high,
            'Minimum': quantiles[0],
            'Q1 (25%)': quantiles[1],
            'Median': quantiles[2],
            'Q3 (75%)': quantiles[3],
            'Maximum': quantiles[4]
        }

    def estimate_required_sample_size(self, error_percentage: float, z: float = 1.96) -> int:
        E = self.mean * error_percentage
        n_req = ((z * self.std) / E) ** 2
        return int(np.ceil(n_req))

    def test_normality(self) -> Tuple[float, float, bool]:
        w_stat, p_val = stats.shapiro(self.data)
        is_normal = p_val > 0.05
        return w_stat, p_val, is_normal


class StatisticalAnalyzer:
    def __init__(self, sample1: SampleDataset, sample2: SampleDataset):
        self.s1 = sample1
        self.s2 = sample2

    def test_homoscedasticity(self) -> Tuple[float, float, bool]:
        f_stat, p_val = stats.levene(self.s1.data, self.s2.data, center='median')
        is_homoscedastic = p_val > 0.05
        return f_stat, p_val, is_homoscedastic

    def run_comparison_tests(self) -> Dict[str, Tuple[float, float]]:
        t_stat, p_welch = stats.ttest_ind(self.s1.data, self.s2.data, equal_var=False)
        w_stat, p_wilcoxon = stats.ranksums(self.s1.data, self.s2.data)

        return {
            'Welch t-test': (t_stat, p_welch),
            'Wilcoxon test': (w_stat, p_wilcoxon)
        }


class BenchmarkVisualizer:
    @staticmethod
    def plot_comparison(sample1: SampleDataset, sample2: SampleDataset, save_path: str = None):
        sns.set_theme(style="whitegrid")
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        sns.boxplot(data=[sample1.data, sample2.data], ax=axes[0], palette="Set2")
        axes[0].set_xticklabels([sample1.device.capitalize(), sample2.device.capitalize()])
        axes[0].set_ylabel('Execution Time (ms)')
        axes[0].set_title(f'Comparative Boxplot (N={sample1.n_bodies})')

        means = [sample1.mean, sample2.mean]
        errors = [
            sample1.mean - sample1.confidence_interval_95[0],
            sample2.mean - sample2.confidence_interval_95[0]
        ]
        axes[1].errorbar(
            [sample1.device.capitalize(), sample2.device.capitalize()],
            means, yerr=errors, fmt='o', capsize=8, color='crimson', elinewidth=2
        )
        axes[1].set_ylabel('Mean Time (ms)')
        axes[1].set_title(f'95% Confidence Intervals (N={sample1.n_bodies})')

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path)
            print(f"[VISUALIZER] Graph saved in: {save_path}")
        plt.show()


class BenchmarkPipelineManager:
    def __init__(self, body_sizes=None):
        self.body_sizes = body_sizes or [10000, 100000, 1000000]

    def run_full_analysis(self):
        for n_bodies in self.body_sizes:
            print(f"\n==================================================")
            print(f"STATISTICAL ANALYSIS WITH N = {n_bodies} BODIES")
            print(f"==================================================")

            laptop_ds = SampleDataset(device='laptop', n_bodies=n_bodies)
            desktop_ds = SampleDataset(device='desktop', n_bodies=n_bodies)

            df_stats = pd.DataFrame({
                'Laptop': laptop_ds.get_summary_stats(),
                'Desktop': desktop_ds.get_summary_stats()
            })
            print("\n--- SUMMARY STATISTICS ---")
            print(df_stats.round(2))

            print("\n--- ESTIMATE OF THE THEORETICAL SAMPLE SIZE (n) ---")
            for err in [0.05, 0.08, 0.10]:
                n_lap = laptop_ds.estimate_required_sample_size(err)
                n_desk = desktop_ds.estimate_required_sample_size(err)
                print(f"Errore {int(err*100)}%: Laptop n={n_lap}, Desktop n={n_desk}")

            print("\n--- TEST DI NORMALITÀ (Shapiro-Wilk) ---")
            for ds in [laptop_ds, desktop_ds]:
                w, p, norm = ds.test_normality()
                status = "NORMALE" if norm else "NON NORMALE"
                print(f"{ds.device.capitalize()}: W={w:.4f}, p-value={p:.4f} -> {status}")

            analyzer = StatisticalAnalyzer(laptop_ds, desktop_ds)
            f_stat, p_homo, is_homo = analyzer.test_homoscedasticity()
            print("\n--- TEST FOR HOMOSCEDASTICITY (Brown-Forsythe) ---")
            print(f"F={f_stat:.4f}, p-value={p_homo:.4e} -> {'HOMOSCEDASTICITY' if is_homo else 'HETEROSCEDASTIC'}")

            print("\n--- COMPARATIVE STATISTICAL TESTS ---")
            results = analyzer.run_comparison_tests()
            for test_name, (stat, p_val) in results.items():
                print(f"{test_name}: Stat={stat:.4f}, p-value={p_val:.4e}")

            BenchmarkVisualizer.plot_comparison(
                laptop_ds, desktop_ds, save_path=f"confronto_{n_bodies}.png"
            )


if __name__ == "__main__":
    pipeline = BenchmarkPipelineManager()
    pipeline.run_full_analysis()