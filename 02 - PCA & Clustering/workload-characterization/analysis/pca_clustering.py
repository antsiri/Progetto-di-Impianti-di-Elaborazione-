"""
 * author Antonio Sirignano
 * created on 23-08-2026-14h-41m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import argparse
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path
from dataclasses import dataclass, field

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA, IncrementalPCA
from sklearn.cluster import Birch
from scipy.cluster.hierarchy import linkage, dendrogram, fcluster
from scipy.spatial.distance import pdist

@dataclass
class PCAResult:
    scaler: StandardScaler
    pca: PCA
    components_df: pd.DataFrame
    explained_variance_ratio: np.ndarray
    cumulative_variance: np.ndarray
    feature_names: list

@dataclass
class ClusteringRun:
    n_components: int
    n_clusters: int
    labels: np.ndarray
    intra_cluster_deviance: float
    inter_cluster_deviance: float
    total_deviance_loss: float

def load_numeric_features(csv_path: Path, exclude_columns: list[str]) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    usable = df.drop(columns=[c for c in exclude_columns if c in df.columns], errors="ignore")
    numeric = usable.select_dtypes(include="number")

    dropped_not_numeric = set(usable.columns) - set(numeric.columns)
    if dropped_not_numeric:
        print(f"[WARN] Numeric columns ignored (not explicitally excluded): {dropped_not_numeric}")

    return numeric

def get_numeric_feature_names(csv_path: Path, exclude_columns: list[str]) -> list[str]:
    header_df = pd.read_csv(csv_path, nrows=5)
    usable = header_df.drop(columns=[c for c in exclude_columns if c in header_df.columns], errors="ignore")
    numeric = usable.select_dtypes(include="number")
    return list(numeric.columns)

def run_pca(features: pd.DataFrame, n_components: int | None = None) -> PCAResult:
    scaler = StandardScaler()
    scaled = scaler.fit_transform(features)

    pca = PCA(n_components=n_components)
    transformed = pca.fit_transform(scaled)

    components_df = pd.DataFrame(
        transformed, 
        columns=[f"PC{i+1}" for i in range(transformed.shape[1])]
    )

    cumulative = np.cumsum(pca.explained_variance_ratio_)

    return PCAResult(
        scaler=scaler,
        pca=pca,
        components_df=components_df,
        explained_variance_ratio=pca.explained_variance_ratio_,
        cumulative_variance=cumulative,
        feature_names=list(features.columns),
    )

def plot_scree(pca_result: PCAResult, output_path: Path):
    fig, ax1 = plt.subplots(figsize=(9, 5))

    n = len(pca_result.explained_variance_ratio)
    ax1.bar(range(1, n+1), pca_result.explained_variance_ratio * 100, color="#8fae8f")
    ax1.set_xlabel("Principal component")
    ax1.set_ylabel("Explained Variance (%)")

    ax2 = ax1.twinx()
    ax2.plot(range(1, n+1), pca_result.cumulative_variance * 100, color="red", marker="o")
    ax2.set_ylabel("Cumulative variance (%)")
    ax2.axhline(y=80, color="gray", linestyle="--", alpha=0.5)

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path)
    plt.close(fig)

def choose_n_components(pca_result: PCAResult, variance_threshold: float = 0.8) -> int:
    idx = np.searchsorted(pca_result.cumulative_variance, variance_threshold) + 1
    return min(idx, len(pca_result.cumulative_variance))



def hierachical_clustering(components: np.ndarray, n_cluseter: int, method: str = "ward") -> np.ndarray:
    Z = linkage(components, method=method)
    labels = fcluster(Z, t=n_cluseter, criterion="maxclust")
    return labels, Z

def plot_dendrogram(Z, outpath_path: Path, title: str = "Dendrogram"):
    fig, ax = plt.subplots(figsize=(10, 12))
    dendrogram(Z, ax=ax, orientation="left", no_labels=True)
    ax.set_title(title)
    fig.tight_layout()
    outpath_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outpath_path)
    plt.close(fig)

def compute_deviance(components: np.ndarray, labels: np.ndarray) -> tuple[float, float, float]:
    total_variance = np.sum(np.var(components, axis=0)) * len(components)

    intra = 0.0
    for cluster_id in np.unique(labels):
        cluster_points = components[labels == cluster_id]
        centroid = cluster_points.mean(axis=0)
        intra += np.sum((cluster_points - centroid) ** 2)

    intra_ratio = intra / total_variance if total_variance > 0 else 0.0
    inter_ratio = 1 - intra_ratio
    total_loss = intra_ratio

    return intra_ratio, inter_ratio, total_loss



def sweep_pca_clustering(features: pd.DataFrame, component_options: list[int], cluster_options: list[int], method: str = "ward") -> list[ClusteringRun]:
    results = []
    for n_comp in component_options:
        pca_result = run_pca(features, n_components=n_comp)
        components = pca_result.components_df.values

        for n_clust in cluster_options:
            labels, _ = hierachical_clustering(components, n_clust, method=method)
            intra, inter, loss = compute_deviance(components, labels)

            results.append(ClusteringRun(
                n_components=n_comp,
                n_clusters=n_clust,
                labels=labels,
                intra_cluster_deviance=round(intra, 4),
                inter_cluster_deviance=round(inter, 4),
                total_deviance_loss=round(loss, 4)
            ))

    return results

def sweep_results_to_dataframe(results: list[ClusteringRun]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "n_components": r.n_components,
            "n_clusters": r.n_clusters,
            "intra_cluster_deviance": r.intra_cluster_deviance,
            "inter_cluster_deviance": r.inter_cluster_deviance,
            "total_deviance_loss": r.total_deviance_loss
        }
        for r in results
    ])

def plot_deviance_curves(sweep_df: pd.DataFrame, output_path: Path):
    fig, ax = plt.subplots(figsize=(9, 6))
    for n_comp in sorted(sweep_df["n_components"].unique()):
        subset = sweep_df[sweep_df["n_components"] == n_comp].sort_values("n_clusters", ascending=False)
        ax.plot(subset["n_clusters"].astype(str), subset["total_deviance_loss"], marker='o', label=f"{n_comp} PCA") 

    ax.set_xlabel("# Cluster")
    ax.set_ylabel("Deviance Loss")
    ax.set_title("Deviance loss PCA + Clustering")
    ax.legend()
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path)
    plt.close()


def extract_cluster_samples(components: np.ndarray, labels: np.ndarray, strategy: str = "nearest_centroid", random_state: int = 42) -> dict[int, int]:
    rng = np.random.default_rng(random_state)
    selected = {}

    for cluster_id in np.unique(labels):
        idx = np.where(labels == cluster_id)[0]
        cluster_points = components[idx]

        if strategy == "random":
            chosen = rng.choice(idx)
        elif strategy == "nearest_centroid":
            centroid = cluster_points.mean(axis=0)
            distances = np.linalg.norm(cluster_points - centroid, axis=1)
            chosen = idx[np.argmin(distances)]
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        selected[int(cluster_id)] = int(chosen)

    return selected

def maybe_subsample(features: pd.DataFrame, max_rows: int, random_state: int = 42) -> pd.DataFrame:
    if len(features) <= max_rows:
        return features

    print(f"[INFO] Dataset with {len(features)} rows > {max_rows}: subsampling for hierarchical cluestering.")
    return features.sample(n=max_rows, random_state=random_state).reset_index(drop=True)


def fit_scaler_incremental(csv_path: Path, feature_columns: list[str], chunksize: int) -> StandardScaler:
    scaler = StandardScaler()
    for chunk in pd.read_csv(csv_path, usecols=feature_columns, chunksize=chunksize):
        scaler.partial_fit(chunk.values)
    return scaler

def fit_ipca_incremental(csv_path: Path, feature_columns: list[str], scaler: StandardScaler,
                         n_components: int, chunksize: int) -> IncrementalPCA:
    ipca = IncrementalPCA(n_components=n_components, batch_size=chunksize)
    for chunk in pd.read_csv(csv_path, usecols=feature_columns, chunksize=chunksize):
        scaled = scaler.transform(chunk.values)
        if len(scaled) >= n_components:
            ipca.partial_fit(scaled)

    return ipca

def fit_birch_incremental(csv_path: Path, feature_columns: list[str], scaler: StandardScaler, 
                          ipca: IncrementalPCA, threshold: float, chunksize: int) -> Birch:
    birch = Birch(n_clusters=None, threshold=threshold)
    for chunk in pd.read_csv(csv_path, usecols=feature_columns, chunksize=chunksize):
        scaled = scaler.transform(chunk.values)
        projected = ipca.transform(scaled)
        birch.partial_fit(projected)

    return birch

def assign_labels_and_counts(csv_path: Path, feature_columns: list[str], scaler: StandardScaler,
                             ipca: IncrementalPCA, birch: Birch, chunksize: int) -> tuple[np.ndarray, np.ndarray]:
    all_labels = []
    for chunk in pd.read_csv(csv_path, usecols=feature_columns, chunksize=chunksize):
        scaled = scaler.transform(chunk.values)
        projected = ipca.transform(scaled)
        labels = birch.predict(projected)
        all_labels.append(labels)

    all_labels = np.concatenate(all_labels)
    counts = np.bincount(all_labels, minlength=len(birch.subcluster_centers_))
    return all_labels, counts

def run_standard_pipeline(input_path: Path, exclude_columns: list[str], component_options: list[int],
                          cluster_options: list[int], variance_threshold: float, linkage_method: str,
                          max_rows_hierarchical: int, output_dir: Path):
   
    features_full = load_numeric_features(input_path, exclude_columns)
    print(f"Used features for PCA ({len(features_full.columns)}): {list(features_full.columns)}")

    max_valid_components = min(features_full.shape)
    valid_component_options = [c for c in component_options if c <= max_valid_components]
    if len(valid_component_options) < len(component_options):
        dropped = set(component_options) - set(valid_component_options)
        print(f"[WARN] Removed component_options not valid (> {max_valid_components} avaiable features): {sorted(dropped)}")
    if not valid_component_options:
        raise ValueError(f"No valid component_options: dataset with only {features_full.shape[1]} features.")

    full_pca = run_pca(features_full, n_components=None)
    plot_scree(full_pca, output_dir / "scree_plot.png")
    suggested_n = choose_n_components(full_pca, variance_threshold)
    print(f"Suggested components for {variance_threshold*100:.0f}% variance: {suggested_n}")


    features = maybe_subsample(features_full, max_rows_hierarchical)

    sweep_results = sweep_pca_clustering(features, valid_component_options, cluster_options, linkage_method)
    sweep_df = sweep_results_to_dataframe(sweep_results)
    print("\n=== Deviance sweep ===")
    print(sweep_df.to_string(index=False))

    sweep_df.to_csv(output_dir / "deviance_sweep.csv", index=False)
    plot_deviance_curves(sweep_df, output_dir / "deviance_loss_curves.png")

    chosen_n_comp = valid_component_options[0]
    pca_for_dendro = run_pca(features, n_components=chosen_n_comp)
    _, Z = hierachical_clustering(pca_for_dendro.components_df.values, n_cluseter=cluster_options[0], method=linkage_method)
    plot_dendrogram(Z, output_dir / "dendrogram.png", title=f"Dendrogramma — {chosen_n_comp} PCA")

    print(f"\nOutput saved in: {output_dir}")

def run_chunked_pipeline(input_path: Path, exlude_columns: list[str], n_components: int,
                         n_final_clusters: int, birch_threshold: float, chunksize: int,
                         linkage_method: str, output_dir: Path) -> dict:
    
    features_columns = get_numeric_feature_names(input_path, exlude_columns)
    print(f"Used features for PCA ({len(features_columns)}): {features_columns}")

    print(f"[1/5] Incremental fitting scaler on {input_path.name}.\n")
    scaler = fit_scaler_incremental(input_path, features_columns, chunksize)

    print(f"[2/5] Fitting IncrementalPCA ({n_components} components).\n")
    ipca = fit_ipca_incremental(input_path, features_columns, scaler, n_components, chunksize)
    print(f"\tExplained Cumulative Variance: {ipca.explained_variance_ratio_.sum():.4f}")

    print(f"[3/5] CF-tree construction with Birch (threshold={birch_threshold}).\n")
    birch = fit_birch_incremental(input_path, features_columns, scaler, ipca, birch_threshold, chunksize)
    n_subclusters = len(birch.subcluster_centers_)
    print(f"\tGenerated sub-cluster: {n_subclusters}")

    print(f"[4/5] Final hierarchical clustering on {n_subclusters} sub-clusters -> {n_final_clusters} cluster.\n")
    final_labels, Z = hierachical_clustering(birch.subcluster_centers_, n_cluseter=n_final_clusters, method=linkage_method)

    output_dir.mkdir(parents=True, exist_ok=True)
    plot_dendrogram(Z, output_dir / "dendrogram.png", title=f"Dendrogram (chunked, {n_subclusters} sub-clusters)")

    intra, inter, loss = compute_deviance(birch.subcluster_centers_, final_labels)
    print(f"\tIntra: {intra:.4f}, Inter: {inter:.4f}, Loss: {loss:.4f} (Evaluated on sub-clusters)")

    print(f"[5/5] Assigning labels on whole dataset.\n")
    row_subcluster_labels, subcluster_counts = assign_labels_and_counts(input_path, features_columns, scaler, ipca, birch, chunksize)
    subcluster_to_final = {i: final_labels[i] for i in range(n_subclusters)}
    row_final_labels = np.array([subcluster_to_final[l] for l in row_subcluster_labels])

    summary_df = pd.DataFrame({
        "n_components": [n_components], "n_clusters": [n_final_clusters],
        "n_subclusters": [n_subclusters],
        "intra_cluster_deviance": [round(intra, 4)],
        "inter_cluster_deviance": [round(inter, 4)],
        "total_deviance_loss": [round(loss, 4)],
    })
    summary_df.to_csv(output_dir / "deviance_summary.csv", index=False)
    print("\n=== Deviance summary (chunked) ===")
    print(summary_df.to_string(index=False))
    print(f"\nOutput saved in: {output_dir}")

    return {
        "scaler": scaler, "ipca": ipca, "birch": birch,
        "row_final_labels": row_final_labels,
        "subcluster_counts": subcluster_counts,
        "intra_cluster_deviance": intra,
        "inter_cluster_deviance": inter,
        "total_deviance_loss": loss,
    }


# CLI
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PCA + Hierarchical Clustering pipeline (standard o chunked)")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--strategy", type=str, choices=["standard", "chunked"], default="standard",
                        help="'standard': tutto in RAM (dataset piccoli). 'chunked': streaming a blocchi (dataset enormi).")
    parser.add_argument("--exclude-columns", nargs="*", default=["timestamp", "timeStamp", "label", "threadName", "URL"])

    # Argomenti modalità standard
    parser.add_argument("--component-options", nargs="+", type=int, default=[3, 4, 5, 6])
    parser.add_argument("--cluster-options", nargs="+", type=int, default=[15, 10, 5, 3])
    parser.add_argument("--max-rows-hierarchical", type=int, default=5000)

    # Argomenti modalità chunked
    parser.add_argument("--n-components", type=int, default=3, help="[chunked] numero fisso di componenti PCA")
    parser.add_argument("--n-clusters", type=int, default=15, help="[chunked] numero finale di cluster")
    parser.add_argument("--birch-threshold", type=float, default=0.5, help="[chunked] soglia CF-tree di Birch")
    parser.add_argument("--chunksize", type=int, default=50_000, help="[chunked] righe lette per blocco")

    # Comuni
    parser.add_argument("--variance-threshold", type=float, default=0.80)
    parser.add_argument("--linkage-method", type=str, default="ward")
    parser.add_argument("--sample-strategy", type=str, default="nearest_centroid")
    parser.add_argument("--output-dir", type=Path, default=None)

    args = parser.parse_args()
    output_dir = args.output_dir or Path("analysis/plots") / f"{args.input.stem}_pca_{args.strategy}"
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.strategy == "standard":
        run_standard_pipeline(
            input_path=args.input, exclude_columns=args.exclude_columns,
            component_options=args.component_options, cluster_options=args.cluster_options,
            variance_threshold=args.variance_threshold, linkage_method=args.linkage_method,
            max_rows_hierarchical=args.max_rows_hierarchical, output_dir=output_dir,
        )
    else:  # chunked
        result = run_chunked_pipeline(
            input_path=args.input, exlude_columns=args.exclude_columns,
            n_components=args.n_components, n_final_clusters=args.n_clusters,
            birch_threshold=args.birch_threshold, chunksize=args.chunksize,
            linkage_method=args.linkage_method, output_dir=output_dir,
        )

        np.save(output_dir / "row_final_labels.npy", result["row_final_labels"])
        print(f"Cluster labels saved in: {output_dir / 'row_final_labels.npy'}")