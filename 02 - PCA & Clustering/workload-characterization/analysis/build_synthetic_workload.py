"""
 * author Antonio Sirignano
 * created on 25-08-2026-14h-14m
 * github: https://github.com/antsiri
 * copyright 2026

Build a synthetic workload from the clustering results.

Each cluster of requests is mapped to its most frequent resource (URL label);
the resources are then weighted by the size of the clusters they represent,
so that the synthetic load generator can reproduce the real traffic mix.
"""

import pandas as pd
import numpy as np

from pathlib import Path

from analysis.pca_clustering import get_numeric_feature_names, fit_scaler_incremental, fit_ipca_incremental
from analysis.pca_clustering import fit_birch_incremental, hierachical_clustering, assign_labels_and_counts


def build_contigency_table(csv_path: Path, row_final_labels: np.ndarray, label_column: str = "label") -> pd.DataFrame:
    """
    Cross-tabulate cluster labels against the requested resource.

    Args:
        csv_path (Path): original CSV (same rows used for clustering).
        row_final_labels (np.ndarray): final cluster label of every row.
        label_column (str): CSV column holding the resource name.

    Returns:
        pandas.DataFrame: contingency table (rows = clusters, columns = resources).

    Raises:
        ValueError: if the CSV and the label array have different lengths.
    """
    # Read only the resource column to keep memory usage low
    label_series = pd.read_csv(csv_path, usecols=[label_column])[label_column]

    if len(label_series) != len(row_final_labels):
        raise ValueError(
            f"Mismatch: {len(label_series)} rows of label vs {len(row_final_labels)} clusters labels"
            "Verify that CSV is not change between the two reading,"
        )

    contigency = pd.crosstab(row_final_labels, label_series)
    return contigency


def most_frequent_resource_per_cluster(contigency: pd.DataFrame) -> pd.Series:
    """
    Return, for each cluster, the resource with the highest count.

    Args:
        contigency (pandas.DataFrame): table from :func:`build_contigency_table`.

    Returns:
        pandas.Series: index = cluster id, value = dominant resource.
    """
    return contigency.idxmax(axis=1)


def build_synthetic_manifest(csv_path: Path, row_final_labels: np.ndarray, label_column: str = "label") -> pd.DataFrame:
    """
    Build the per-cluster manifest of the synthetic workload.

    Args:
        csv_path (Path): original CSV.
        row_final_labels (np.ndarray): final cluster label of every row.
        label_column (str): CSV column holding the resource name.

    Returns:
        pandas.DataFrame: columns ``cluster``, ``resource`` (dominant resource),
        ``count_in_cluster`` (occurrences of that resource) and
        ``cluster_size`` (total rows in the cluster), sorted by cluster.
    """
    contigency = build_contigency_table(csv_path, row_final_labels, label_column)
    top_resources = most_frequent_resource_per_cluster(contigency)

    result = pd.DataFrame({
        "cluster": top_resources.index,
        "resource": top_resources.values,
        # Number of times the dominant resource appears in its cluster
        "count_in_cluster": [contigency.loc[c, r] for c, r in zip(top_resources.index, top_resources.values)],
        "cluster_size": contigency.sum(axis=1).values,
    })

    return result.sort_values("cluster").reset_index(drop=True)


def build_weighted_synthetic_pool(manifest: pd.DataFrame, min_cluster_size: int = 50, total_weight_budget: int = 100) -> pd.DataFrame:
    """
    Turn the manifest into a weighted pool of resources.

    Clusters smaller than ``min_cluster_size`` are discarded; the remaining
    ones are aggregated by resource and receive an integer weight proportional
    to their share of traffic (sum of weights ≈ ``total_weight_budget``).

    Args:
        manifest (pandas.DataFrame): output of :func:`build_synthetic_manifest`.
        min_cluster_size (int): minimum rows for a cluster to be kept.
        total_weight_budget (int): total weight to distribute.

    Returns:
        pandas.DataFrame: columns ``resource``, ``cluster_size``, ``weight``,
        sorted by decreasing weight.

    Raises:
        ValueError: if no cluster reaches ``min_cluster_size``.
    """

    # Keep only clusters that are large enough to be representative
    filtered = manifest[manifest["cluster_size"] >= min_cluster_size].copy()

    if filtered.empty:
        raise ValueError(f"No cluster over min_cluster_size={min_cluster_size}")

    # Report how much traffic is lost by discarding the minor clusters
    dropped = len(manifest) - len(filtered)
    if dropped > 0:
        dropped_share = manifest.loc[~manifest.index.isin(filtered.index), "cluster_size"].sum() / manifest["cluster_size"].sum()
        print(f"[INFO] Dropped {dropped} minor clusters (< {min_cluster_size} rows), "
              f"that cover only {dropped_share*100:.3f}% of total traffic.")

    # Several clusters may share the same dominant resource: sum their sizes
    aggregated = filtered.groupby("resource")["cluster_size"].sum().reset_index()

    # Integer weight proportional to the traffic share (at least 1)
    total_size = aggregated["cluster_size"].sum()
    aggregated["weight"] = (aggregated["cluster_size"] / total_size * total_weight_budget).round().astype(int)
    aggregated["weight"] = aggregated["weight"].clip(lower=1)

    return aggregated.sort_values("weight", ascending=False).reset_index(drop=True)
