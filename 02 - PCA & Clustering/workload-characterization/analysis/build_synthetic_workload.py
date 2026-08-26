"""
 * author Antonio Sirignano
 * created on 25-08-2026-14h-14m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import pandas as pd
import numpy as np

from pathlib import Path

from analysis.pca_clustering import get_numeric_feature_names, fit_scaler_incremental, fit_ipca_incremental
from analysis.pca_clustering import fit_birch_incremental, hierachical_clustering, assign_labels_and_counts

def build_contigency_table(csv_path: Path, row_final_labels: np.ndarray, label_column: str = "label") -> pd.DataFrame:
    label_series = pd.read_csv(csv_path, usecols=[label_column])[label_column]

    if len(label_series) != len(row_final_labels):
        raise ValueError(
            f"Mismatch: {len(label_series)} rows of label vs {len(row_final_labels)} clusters labels"
            "Verify that CSV is not change between the two reading,"
        )

    contigency = pd.crosstab(row_final_labels, label_series)
    return contigency

def most_frequent_resource_per_cluster(contigency: pd.DataFrame) -> pd.Series:
    return contigency.idxmax(axis=1)

def build_synthetic_manifest(csv_path: Path, row_final_labels: np.ndarray, label_column: str = "label") -> pd.DataFrame:
    contigency = build_contigency_table(csv_path, row_final_labels, label_column)
    top_resources = most_frequent_resource_per_cluster(contigency)

    result = pd.DataFrame({
        "cluster": top_resources.index,
        "resource": top_resources.values, 
        "count_in_cluster": [contigency.loc[c, r] for c, r in zip(top_resources.index, top_resources.values)],
        "cluster_size": contigency.sum(axis=1).values, 
    })

    return result.sort_values("cluster").reset_index(drop=True)

def build_weighted_synthetic_pool(manifest: pd.DataFrame, min_cluster_size: int = 50, total_weight_budget: int = 100) -> pd.DataFrame:
    
    filtered = manifest[manifest["cluster_size"] >= min_cluster_size].copy()

    if filtered.empty:
        raise ValueError(f"No cluster over min_cluster_size={min_cluster_size}")

    dropped = len(manifest) - len(filtered)
    if dropped > 0:
        dropped_share = manifest.loc[~manifest.index.isin(filtered.index), "cluster_size"].sum() / manifest["cluster_size"].sum()
        print(f"[INFO] Dropped {dropped} minor clusters (< {min_cluster_size} rows), "
              f"that cover only {dropped_share*100:.3f}% of total traffic.")

    aggregated = filtered.groupby("resource")["cluster_size"].sum().reset_index()

    total_size = aggregated["cluster_size"].sum()
    aggregated["weight"] = (aggregated["cluster_size"] / total_size * total_weight_budget).round().astype(int)
    aggregated["weight"] = aggregated["weight"].clip(lower=1) 

    return aggregated.sort_values("weight", ascending=False).reset_index(drop=True)