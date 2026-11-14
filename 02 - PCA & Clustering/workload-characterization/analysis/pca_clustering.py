"""
 * author Antonio Sirignano
 * created on 23-08-2026-14h-41m
 * github: https://github.com/antsiri
 * copyright 2026

PCA + hierarchical clustering pipeline for workload characterization.

Two strategies are available:
    * ``standard``: the whole dataset is loaded in RAM; a sweep over several
      (n_components, n_clusters) pairs is performed and the deviance loss of
      each configuration is plotted (suitable for small datasets).
    * ``chunked``: the dataset is streamed in blocks; StandardScaler,
      IncrementalPCA and Birch (CF-tree) are fitted incrementally and the
      final hierarchical clustering is run on the Birch sub-cluster centres
      (suitable for very large datasets).
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
    """
    Output of :func:`run_pca`.

    Attributes:
        scaler: fitted StandardScaler.
        pca: fitted PCA model.
        components_df: data projected on the principal components (``PC1..PCn``).
        explained_variance_ratio: variance explained by each component.
        cumulative_variance: cumulative explained variance.
        feature_names: names of the original features.
    """
    scaler: StandardScaler
    pca: PCA
    components_df: pd.DataFrame
    explained_variance_ratio: np.ndarray
    cumulative_variance: np.ndarray
    feature_names: list


@dataclass
class ClusteringRun:
    """
    Result of one (n_components, n_clusters) configuration of the sweep.

    Attributes:
        n_components: number of PCA components used.
        n_clusters: number of clusters formed.
        labels: cluster label of each row.
        intra_cluster_deviance: within-cluster deviance / total deviance.
        inter_cluster_deviance: between-cluster deviance / total deviance.
        total_deviance_loss: information lost by clustering (= intra ratio).
    """
    n_components: int
    n_clusters: int
    labels: np.ndarray
    intra_cluster_deviance: float
    inter_cluster_deviance: float
    total_deviance_loss: float


def load_numeric_features(csv_path: Path, exclude_columns: list[str]) -> pd.DataFrame:
    """
    Load a CSV and keep only the numeric feature columns.

    Args:
        csv_path (Path): dataset to load.
        exclude_columns (list[str]): columns to drop explicitly (ids, labels...).

    Returns:
        pandas.DataFrame: numeric features only.
    """
    df = pd.read_csv(csv_path)
    usable = df.drop(columns=[c for c in exclude_columns if c in df.columns], errors="ignore")
    numeric = usable.select_dtypes(include="number")

    # Warn about non-numeric columns that were silently discarded
    dropped_not_numeric = set(usable.columns) - set(numeric.columns)
    if dropped_not_numeric:
        print(f"[WARN] Numeric columns ignored (not explicitally excluded): {dropped_not_numeric}")

    return numeric


def get_numeric_feature_names(csv_path: Path, exclude_columns: list[str]) -> list[str]:
    """
    Return the names of the numeric feature columns reading only the first
    rows of the CSV (used by the chunked pipeline to avoid loading everything).

    Args:
        csv_path (Path): dataset.
        exclude_columns (list[str]): columns to ignore.

    Returns:
        list[str]: numeric feature names.
    """
    # A few rows are enough for pandas to infer the column dtypes
    header_df = pd.read_csv(csv_path, nrows=5)
    usable = header_df.drop(columns=[c for c in exclude_columns if c in header_df.columns], errors="ignore")
    numeric = usable.select_dtypes(include="number")
    return list(numeric.columns)


def run_pca(features: pd.DataFrame, n_components: int | None = None) -> PCAResult:
    """
    Standardise the features and run PCA.

    Args:
        features (pandas.DataFrame): numeric features.
        n_components (int | None): components to keep (None = all).

    Returns:
        PCAResult: fitted models, projected data and explained variance.
    """
    # Standardisation (zero mean, unit variance) is required because features have different units
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
    """
    Save the scree plot: explained variance per component (bars) and
    cumulative variance (line) with an 80% reference line.

    Args:
        pca_result (PCAResult): result of a full PCA.
        output_path (Path): image file to write.
    """
    fig, ax1 = plt.subplots(figsize=(9, 5))

    n = len(pca_result.explained_variance_ratio)
    ax1.bar(range(1, n+1), pca_result.explained_variance_ratio * 100, color="#8fae8f")
    ax1.set_xlabel("Principal component")
    ax1.set_ylabel("Explained Variance (%)")

    # Secondary axis for the cumulative variance curve
    ax2 = ax1.twinx()
    ax2.plot(range(1, n+1), pca_result.cumulative_variance * 100, color="red", marker="o")
    ax2.set_ylabel("Cumulative variance (%)")
    ax2.axhline(y=80, color="gray", linestyle="--", alpha=0.5)

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path)
    plt.close(fig)


def choose_n_components(pca_result: PCAResult, variance_threshold: float = 0.8) -> int:
    """
    Smallest number of components whose cumulative variance reaches
    ``variance_threshold``.

    Args:
        pca_result (PCAResult): result of a full PCA.
        variance_threshold (float): target cumulative variance (0-1).

    Returns:
        int: suggested number of components.
    """
    # searchsorted gives the 0-based index of the first value >= threshold
    idx = np.searchsorted(pca_result.cumulative_variance, variance_threshold) + 1
    return min(idx, len(pca_result.cumulative_variance))



def hierachical_clustering(components: np.ndarray, n_cluseter: int, method: str = "ward") -> np.ndarray:
    """
    Agglomerative hierarchical clustering cut at ``n_cluseter`` clusters.

    Args:
        components (np.ndarray): points to cluster (e.g. PCA scores).
        n_cluseter (int): desired number of clusters.
        method (str): linkage criterion (``"ward"``, ``"average"``...).

    Returns:
        tuple[np.ndarray, np.ndarray]: cluster labels (1-based) and linkage matrix ``Z``.
    """
    # Build the full linkage tree, then cut it to obtain at most n_cluseter clusters
    Z = linkage(components, method=method)
    labels = fcluster(Z, t=n_cluseter, criterion="maxclust")
    return labels, Z


def plot_dendrogram(Z, outpath_path: Path, title: str = "Dendrogram"):
    """
    Save the dendrogram of a linkage matrix.

    Args:
        Z (np.ndarray): linkage matrix.
        outpath_path (Path): image file to write.
        title (str): plot title.
    """
    fig, ax = plt.subplots(figsize=(10, 12))
    dendrogram(Z, ax=ax, orientation="left", no_labels=True)
    ax.set_title(title)
    fig.tight_layout()
    outpath_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outpath_path)
    plt.close(fig)


def compute_deviance(components: np.ndarray, labels: np.ndarray) -> tuple[float, float, float]:
    """
    Decompose the total deviance into within- and between-cluster parts.

    Args:
        components (np.ndarray): clustered points.
        labels (np.ndarray): cluster label of each point.

    Returns:
        tuple[float, float, float]: ``(intra_ratio, inter_ratio, total_loss)``,
        where ``total_loss`` equals the intra ratio (information lost by
        replacing each point with its cluster centroid).
    """
    # Total deviance = sum of squared distances from the global mean
    total_variance = np.sum(np.var(components, axis=0)) * len(components)

    # Within-cluster deviance = sum of squared distances from each cluster centroid
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
    """
    Evaluate every combination of number of components and number of clusters.

    Args:
        features (pandas.DataFrame): numeric features.
        component_options (list[int]): PCA component counts to try.
        cluster_options (list[int]): cluster counts to try.
        method (str): linkage criterion.

    Returns:
        list[ClusteringRun]: one entry per configuration.
    """
    results = []
    for n_comp in component_options:
        # PCA is computed once per number of components...
        pca_result = run_pca(features, n_components=n_comp)
        components = pca_result.components_df.values

        # ...and reused for every number of clusters
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
    """
    Convert the sweep results into a table (labels excluded).

    Args:
        results (list[ClusteringRun]): output of :func:`sweep_pca_clustering`.

    Returns:
        pandas.DataFrame: one row per configuration.
    """
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
    """
    Plot deviance loss vs number of clusters, one curve per number of components.

    Args:
        sweep_df (pandas.DataFrame): output of :func:`sweep_results_to_dataframe`.
        output_path (Path): image file to write.
    """
    fig, ax = plt.subplots(figsize=(9, 6))
    for n_comp in sorted(sweep_df["n_components"].unique()):
        # Clusters in decreasing order so the x-axis goes from fine to coarse clustering
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
    """
    Pick one representative row for every cluster.

    Args:
        components (np.ndarray): clustered points.
        labels (np.ndarray): cluster label of each point.
        strategy (str): ``"nearest_centroid"`` (closest point to the cluster
            mean) or ``"random"``.
        random_state (int): seed for the random strategy.

    Returns:
        dict[int, int]: cluster id -> row index of the chosen sample.

    Raises:
        ValueError: on an unknown strategy.
    """
    rng = np.random.default_rng(random_state)
    selected = {}

    for cluster_id in np.unique(labels):
        # Row indices and coordinates of the points in this cluster
        idx = np.where(labels == cluster_id)[0]
        cluster_points = components[idx]

        if strategy == "random":
            chosen = rng.choice(idx)
        elif strategy == "nearest_centroid":
            # Euclidean distance of every point from the centroid; take the minimum
            centroid = cluster_points.mean(axis=0)
            distances = np.linalg.norm(cluster_points - centroid, axis=1)
            chosen = idx[np.argmin(distances)]
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        selected[int(cluster_id)] = int(chosen)

    return selected


def maybe_subsample(features: pd.DataFrame, max_rows: int, random_state: int = 42) -> pd.DataFrame:
    """
    Randomly subsample the dataset if it exceeds ``max_rows`` rows
    (hierarchical clustering is O(n^2) in memory).

    Args:
        features (pandas.DataFrame): dataset.
        max_rows (int): maximum number of rows to keep.
        random_state (int): sampling seed.

    Returns:
        pandas.DataFrame: original or subsampled dataset.
    """
    if len(features) <= max_rows:
        return features

    print(f"[INFO] Dataset with {len(features)} rows > {max_rows}: subsampling for hierarchical cluestering.")
    return features.sample(n=max_rows, random_state=random_state).reset_index(drop=True)


def fit_scaler_incremental(csv_path: Path, feature_columns: list[str], chunksize: int) -> StandardScaler:
    """
    Fit a StandardScaler reading the CSV in chunks.

    Args:
        csv_path (Path): dataset.
        feature_columns (list[str]): columns to use.
        chunksize (int): rows per chunk.

    Returns:
        StandardScaler: fitted scaler.
    """
    scaler = StandardScaler()
    for chunk in pd.read_csv(csv_path, usecols=feature_columns, chunksize=chunksize):
        # partial_fit updates running mean and variance
        scaler.partial_fit(chunk.values)
    return scaler


def fit_ipca_incremental(csv_path: Path, feature_columns: list[str], scaler: StandardScaler,
                         n_components: int, chunksize: int) -> IncrementalPCA:
    """
    Fit an IncrementalPCA on the standardised data, chunk by chunk.

    Args:
        csv_path (Path): dataset.
        feature_columns (list[str]): columns to use.
        scaler (StandardScaler): already-fitted scaler.
        n_components (int): number of components.
        chunksize (int): rows per chunk.

    Returns:
        IncrementalPCA: fitted model.
    """
    ipca = IncrementalPCA(n_components=n_components, batch_size=chunksize)
    for chunk in pd.read_csv(csv_path, usecols=feature_columns, chunksize=chunksize):
        scaled = scaler.transform(chunk.values)
        # IncrementalPCA requires at least n_components rows per batch (last chunk may be smaller)
        if len(scaled) >= n_components:
            ipca.partial_fit(scaled)

    return ipca


def fit_birch_incremental(csv_path: Path, feature_columns: list[str], scaler: StandardScaler,
                          ipca: IncrementalPCA, threshold: float, chunksize: int) -> Birch:
    """
    Build a Birch CF-tree on the PCA-projected data, chunk by chunk.

    ``n_clusters=None`` keeps the raw sub-clusters; the final clustering is
    done afterwards with hierarchical clustering on their centres.

    Args:
        csv_path (Path): dataset.
        feature_columns (list[str]): columns to use.
        scaler (StandardScaler): fitted scaler.
        ipca (IncrementalPCA): fitted PCA.
        threshold (float): Birch sub-cluster radius threshold.
        chunksize (int): rows per chunk.

    Returns:
        Birch: fitted model.
    """
    birch = Birch(n_clusters=None, threshold=threshold)
    for chunk in pd.read_csv(csv_path, usecols=feature_columns, chunksize=chunksize):
        # Same transformation chain used at fit time: scale -> project -> cluster
        scaled = scaler.transform(chunk.values)
        projected = ipca.transform(scaled)
        birch.partial_fit(projected)

    return birch


def assign_labels_and_counts(csv_path: Path, feature_columns: list[str], scaler: StandardScaler,
                             ipca: IncrementalPCA, birch: Birch, chunksize: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Assign every row of the dataset to its Birch sub-cluster.

    Args:
        csv_path (Path): dataset.
        feature_columns (list[str]): columns to use.
        scaler (StandardScaler): fitted scaler.
        ipca (IncrementalPCA): fitted PCA.
        birch (Birch): fitted Birch model.
        chunksize (int): rows per chunk.

    Returns:
        tuple[np.ndarray, np.ndarray]: sub-cluster label of each row and
        number of rows in each sub-cluster.
    """
    all_labels = []
    for chunk in pd.read_csv(csv_path, usecols=feature_columns, chunksize=chunksize):
        scaled = scaler.transform(chunk.values)
        projected = ipca.transform(scaled)
        labels = birch.predict(projected)
        all_labels.append(labels)

    all_labels = np.concatenate(all_labels)
    # Rows per sub-cluster (minlength guarantees one entry for every sub-cluster)
    counts = np.bincount(all_labels, minlength=len(birch.subcluster_centers_))
    return all_labels, counts


def run_standard_pipeline(input_path: Path, exclude_columns: list[str], component_options: list[int],
                          cluster_options: list[int], variance_threshold: float, linkage_method: str,
                          max_rows_hierarchical: int, output_dir: Path):
    """
    In-memory pipeline: scree plot, (components x clusters) sweep, deviance
    curves and dendrogram.

    Args:
        input_path (Path): cleaned dataset.
        exclude_columns (list[str]): non-feature columns.
        component_options (list[int]): component counts to try.
        cluster_options (list[int]): cluster counts to try.
        variance_threshold (float): target variance for the suggested components.
        linkage_method (str): linkage criterion.
        max_rows_hierarchical (int): subsampling limit for hierarchical clustering.
        output_dir (Path): folder for plots and CSV.

    Raises:
        ValueError: if no component option is compatible with the dataset.
    """

    features_full = load_numeric_features(input_path, exclude_columns)
    print(f"Used features for PCA ({len(features_full.columns)}): {list(features_full.columns)}")

    # The number of components cannot exceed min(n_rows, n_features)
    max_valid_components = min(features_full.shape)
    valid_component_options = [c for c in component_options if c <= max_valid_components]
    if len(valid_component_options) < len(component_options):
        dropped = set(component_options) - set(valid_component_options)
        print(f"[WARN] Removed component_options not valid (> {max_valid_components} avaiable features): {sorted(dropped)}")
    if not valid_component_options:
        raise ValueError(f"No valid component_options: dataset with only {features_full.shape[1]} features.")

    # Full PCA (all components) on the whole dataset -> scree plot and suggestion
    full_pca = run_pca(features_full, n_components=None)
    plot_scree(full_pca, output_dir / "scree_plot.png")
    suggested_n = choose_n_components(full_pca, variance_threshold)
    print(f"Suggested components for {variance_threshold*100:.0f}% variance: {suggested_n}")


    # Hierarchical clustering is expensive: work on a subsample if needed
    features = maybe_subsample(features_full, max_rows_hierarchical)

    sweep_results = sweep_pca_clustering(features, valid_component_options, cluster_options, linkage_method)
    sweep_df = sweep_results_to_dataframe(sweep_results)
    print("\n=== Deviance sweep ===")
    print(sweep_df.to_string(index=False))

    sweep_df.to_csv(output_dir / "deviance_sweep.csv", index=False)
    plot_deviance_curves(sweep_df, output_dir / "deviance_loss_curves.png")

    # Dendrogram built with the first component option and the first cluster option
    chosen_n_comp = valid_component_options[0]
    pca_for_dendro = run_pca(features, n_components=chosen_n_comp)
    _, Z = hierachical_clustering(pca_for_dendro.components_df.values, n_cluseter=cluster_options[0], method=linkage_method)
    plot_dendrogram(Z, output_dir / "dendrogram.png", title=f"Dendrogramma — {chosen_n_comp} PCA")

    print(f"\nOutput saved in: {output_dir}")


def run_chunked_pipeline(input_path: Path, exlude_columns: list[str], n_components: int,
                         n_final_clusters: int, birch_threshold: float, chunksize: int,
                         linkage_method: str, output_dir: Path) -> dict:
    """
    Streaming pipeline for datasets that do not fit in memory.

    Steps: (1) incremental scaler, (2) IncrementalPCA, (3) Birch CF-tree,
    (4) hierarchical clustering of the Birch sub-cluster centres,
    (5) assignment of the final cluster label to every row.

    Args:
        input_path (Path): cleaned dataset.
        exlude_columns (list[str]): non-feature columns.
        n_components (int): number of PCA components.
        n_final_clusters (int): number of final clusters.
        birch_threshold (float): Birch sub-cluster threshold.
        chunksize (int): rows per chunk.
        linkage_method (str): linkage criterion.
        output_dir (Path): folder for plots and CSV.

    Returns:
        dict: fitted models, per-row final labels, sub-cluster counts and deviance values.
    """

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

    # Hierarchical clustering on the (few) sub-cluster centres instead of the (many) rows
    print(f"[4/5] Final hierarchical clustering on {n_subclusters} sub-clusters -> {n_final_clusters} cluster.\n")
    final_labels, Z = hierachical_clustering(birch.subcluster_centers_, n_cluseter=n_final_clusters, method=linkage_method)

    output_dir.mkdir(parents=True, exist_ok=True)
    plot_dendrogram(Z, output_dir / "dendrogram.png", title=f"Dendrogram (chunked, {n_subclusters} sub-clusters)")

    intra, inter, loss = compute_deviance(birch.subcluster_centers_, final_labels)
    print(f"\tIntra: {intra:.4f}, Inter: {inter:.4f}, Loss: {loss:.4f} (Evaluated on sub-clusters)")

    # Row -> sub-cluster -> final cluster
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

    # Standard-mode arguments
    parser.add_argument("--component-options", nargs="+", type=int, default=[3, 4, 5, 6])
    parser.add_argument("--cluster-options", nargs="+", type=int, default=[15, 10, 5, 3])
    parser.add_argument("--max-rows-hierarchical", type=int, default=5000)

    # Chunked-mode arguments
    parser.add_argument("--n-components", type=int, default=3, help="[chunked] numero fisso di componenti PCA")
    parser.add_argument("--n-clusters", type=int, default=15, help="[chunked] numero finale di cluster")
    parser.add_argument("--birch-threshold", type=float, default=0.5, help="[chunked] soglia CF-tree di Birch")
    parser.add_argument("--chunksize", type=int, default=50_000, help="[chunked] righe lette per blocco")

    # Common arguments
    parser.add_argument("--variance-threshold", type=float, default=0.80)
    parser.add_argument("--linkage-method", type=str, default="ward")
    parser.add_argument("--sample-strategy", type=str, default="nearest_centroid")
    parser.add_argument("--output-dir", type=Path, default=None)

    args = parser.parse_args()
    # Default output folder: analysis/plots/<input name>_pca_<strategy>
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

        # Save per-row final labels (used later to build the synthetic workload)
        np.save(output_dir / "row_final_labels.npy", result["row_final_labels"])
        print(f"Cluster labels saved in: {output_dir / 'row_final_labels.npy'}")
