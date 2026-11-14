"""
 * author Antonio Sirignano
 * created on 06-09-2026-18h-27m
 * github: https://github.com/antsiri
 * copyright 2026

Extract one representative sample per cluster in the PCA space.

The dataset is projected on the first principal components, clustered with
hierarchical clustering and, for each cluster, one row is selected (by default
the one closest to the centroid). The selected PC coordinates are saved to CSV
and later used by the hypothesis tests (real vs synthetic workload).
"""

import argparse
import numpy as np
import pandas as pd

from pathlib import Path

from analysis.pca_clustering import load_numeric_features, run_pca, hierachical_clustering, extract_cluster_samples


def extract_and_saves_samples(
        input_path: Path,
        output_path: Path,
        exclude_columns: list[str],
        n_components: int,
        n_clusters: int,
        linkage_method: str = "ward",
        samples_strategy: str = "nearest_centroid"
):
    """
    Run PCA + hierarchical clustering and save one sample per cluster.

    Args:
        input_path (Path): cleaned CSV dataset.
        output_path (Path): destination CSV (columns ``cluster``, ``PC1..PCn``).
        exclude_columns (list[str]): non-feature columns to ignore.
        n_components (int): number of principal components to keep.
        n_clusters (int): number of clusters to form.
        linkage_method (str): linkage criterion (e.g. ``"ward"``).
        samples_strategy (str): how to choose the representative row.

    Returns:
        pandas.DataFrame: the saved samples.
    """
    # 1. Numeric features -> 2. PCA projection
    features = load_numeric_features(input_path, exclude_columns)
    pca_result = run_pca(features, n_components=n_components)
    components = pca_result.components_df.values

    # 3. Hierarchical clustering in the PCA space and representative selection
    labels, _ = hierachical_clustering(components, n_cluseter=n_clusters, method=linkage_method)
    selected = extract_cluster_samples(components, labels, strategy=samples_strategy)

    # Build one output row per cluster with its PC coordinates
    rows = []
    for cluster_id, row_idx in sorted(selected.items()):
        row = {"cluster": cluster_id}
        for i in range(n_components):
            row[f"PC{i+1}"] = components[row_idx, i]
        rows.append(row)

    result_df = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(output_path, index=False)
    print(f"Saved {len(result_df)} cluster samples ({n_components} components) to {output_path}")
    return result_df


if __name__ == "__main__":
    # Command-line interface
    parser = argparse.ArgumentParser(description="Extract representative sample per cluster (PCA space)")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--exclude-columns", nargs="*", default=["timestamp", "timeStamp", "label", "threadName", "URL"])
    parser.add_argument("--n-components", type=int, required=True)
    parser.add_argument("--n-clusters", type=int, required=True)
    parser.add_argument("--linkage-method", type=str, default="ward")
    parser.add_argument("--sample-strategy", type=str, default="nearest_centroid")

    args = parser.parse_args()

    extract_and_saves_samples(
        input_path=args.input,
        output_path=args.output,
        exclude_columns=args.exclude_columns,
        n_components=args.n_components,
        n_clusters=args.n_clusters,
        linkage_method=args.linkage_method,
        samples_strategy=args.sample_strategy
    )
