"""
Canon Ball Analysis Engine
Computes semantic space projections, dispersion metrics, and statistical comparisons
between control (no knowledge layer) and test (with knowledge layer) trials.
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_distances
from scipy.stats import mannwhitneyu
import umap


def collect_embeddings(trials: list[dict]) -> np.ndarray:
    """Flatten all chunk embeddings from a list of trials into a single matrix."""
    all_embs = []
    for t in trials:
        all_embs.extend(t["embeddings"])
    return np.array(all_embs)


def collect_embeddings_by_trial(trials: list[dict]) -> list[np.ndarray]:
    """Return a list of embedding matrices, one per trial."""
    return [np.array(t["embeddings"]) for t in trials]


def compute_centroid(embs: np.ndarray) -> np.ndarray:
    return embs.mean(axis=0)


def compute_dispersion(embs: np.ndarray) -> dict:
    """Measure how spread out the embeddings are — the 'landing zone' size."""
    centroid = compute_centroid(embs)
    dists_to_centroid = np.linalg.norm(embs - centroid, axis=1)
    cosine_dists = cosine_distances(embs, centroid.reshape(1, -1)).flatten()

    return {
        "mean_euclidean_to_centroid": float(dists_to_centroid.mean()),
        "std_euclidean_to_centroid": float(dists_to_centroid.std()),
        "max_euclidean_to_centroid": float(dists_to_centroid.max()),
        "mean_cosine_to_centroid": float(cosine_dists.mean()),
        "std_cosine_to_centroid": float(cosine_dists.std()),
        "n_points": len(embs),
    }


def compute_pairwise_distances(embs: np.ndarray) -> dict:
    """Average pairwise distance within a group — measures internal coherence."""
    if len(embs) < 2:
        return {"mean_pairwise_cosine": 0.0, "std_pairwise_cosine": 0.0}
    pw = cosine_distances(embs)
    upper = pw[np.triu_indices_from(pw, k=1)]
    return {
        "mean_pairwise_cosine": float(upper.mean()),
        "std_pairwise_cosine": float(upper.std()),
    }


def compute_per_trial_centroids(trials: list[dict]) -> np.ndarray:
    """Centroid of each trial's output — where each 'ball' landed."""
    centroids = []
    for t in trials:
        embs = np.array(t["embeddings"])
        centroids.append(embs.mean(axis=0))
    return np.array(centroids)


def compare_groups(control_trials: list[dict], test_trials: list[dict]) -> dict:
    """Statistical comparison of control vs test landing zones."""
    ctrl_centroids = compute_per_trial_centroids(control_trials)
    test_centroids = compute_per_trial_centroids(test_trials)

    ctrl_global_centroid = ctrl_centroids.mean(axis=0)
    test_global_centroid = test_centroids.mean(axis=0)

    ctrl_dists = np.linalg.norm(ctrl_centroids - ctrl_global_centroid, axis=1)
    test_dists = np.linalg.norm(test_centroids - test_global_centroid, axis=1)

    # Mann-Whitney U test: is the dispersion significantly different?
    stat, pvalue = mannwhitneyu(ctrl_dists, test_dists, alternative='two-sided')

    centroid_shift = float(np.linalg.norm(ctrl_global_centroid - test_global_centroid))
    cosine_shift = float(cosine_distances(
        ctrl_global_centroid.reshape(1, -1),
        test_global_centroid.reshape(1, -1)
    )[0, 0])

    return {
        "control_mean_dispersion": float(ctrl_dists.mean()),
        "control_std_dispersion": float(ctrl_dists.std()),
        "test_mean_dispersion": float(test_dists.mean()),
        "test_std_dispersion": float(test_dists.std()),
        "dispersion_ratio": float(test_dists.mean() / ctrl_dists.mean()) if ctrl_dists.mean() > 0 else None,
        "centroid_shift_euclidean": centroid_shift,
        "centroid_shift_cosine": cosine_shift,
        "mann_whitney_stat": float(stat),
        "mann_whitney_pvalue": float(pvalue),
    }


def project_2d(control_trials: list[dict], test_trials: list[dict],
               method: str = "umap") -> dict:
    """Project all embeddings into 2D for visualization."""
    ctrl_embs = collect_embeddings(control_trials)
    test_embs = collect_embeddings(test_trials)
    all_embs = np.vstack([ctrl_embs, test_embs])

    n_ctrl = len(ctrl_embs)

    if method == "umap":
        reducer = umap.UMAP(n_components=2, random_state=42, metric="cosine",
                            n_neighbors=min(15, len(all_embs) - 1))
        projected = reducer.fit_transform(all_embs)
    else:
        from sklearn.manifold import TSNE
        projected = TSNE(n_components=2, random_state=42, metric="cosine",
                         perplexity=min(30, len(all_embs) - 1)).fit_transform(all_embs)

    # Also project per-trial centroids
    ctrl_centroids = compute_per_trial_centroids(control_trials)
    test_centroids = compute_per_trial_centroids(test_trials)
    all_centroids = np.vstack([ctrl_centroids, test_centroids])

    if method == "umap":
        centroid_proj = reducer.transform(all_centroids)
    else:
        # For t-SNE, re-fit with centroids included
        combined = np.vstack([all_embs, all_centroids])
        proj_all = TSNE(n_components=2, random_state=42, metric="cosine",
                        perplexity=min(30, len(combined) - 1)).fit_transform(combined)
        centroid_proj = proj_all[len(all_embs):]

    n_ctrl_centroids = len(ctrl_centroids)

    return {
        "control_points": projected[:n_ctrl].tolist(),
        "test_points": projected[n_ctrl:].tolist(),
        "control_centroids": centroid_proj[:n_ctrl_centroids].tolist(),
        "test_centroids": centroid_proj[n_ctrl_centroids:].tolist(),
    }


def build_trial_labels(trials: list[dict]) -> list[str]:
    """Create labels for each embedding point: trial index + chunk text."""
    labels = []
    for t in trials:
        for chunk in t["output_tokens"]:
            labels.append(f"T{t['trial_index']}: {chunk[:60]}...")
    return labels


from typing import TypedDict


class AnalysisResult(TypedDict):
    comparison: dict
    projection: dict
    control_dispersion: dict
    test_dispersion: dict
    control_pairwise: dict
    test_pairwise: dict
    control_labels: list
    test_labels: list


def full_analysis(experiment_data: dict) -> AnalysisResult:
    """Run complete analysis on an experiment."""
    ctrl = experiment_data["control_trials"]
    test = experiment_data["test_trials"]

    ctrl_embs = collect_embeddings(ctrl)
    test_embs = collect_embeddings(test)

    return AnalysisResult(
        comparison=compare_groups(ctrl, test),
        projection=project_2d(ctrl, test),
        control_dispersion=compute_dispersion(ctrl_embs),
        test_dispersion=compute_dispersion(test_embs),
        control_pairwise=compute_pairwise_distances(ctrl_embs),
        test_pairwise=compute_pairwise_distances(test_embs),
        control_labels=build_trial_labels(ctrl),
        test_labels=build_trial_labels(test),
    )
