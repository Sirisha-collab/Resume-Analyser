from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr


# ----------------------------------------------------------------------
# Ranking metrics
# ----------------------------------------------------------------------
def dcg_at_k(relevances: np.ndarray, k: int) -> float:
    """Discounted Cumulative Gain."""
    rel = np.asarray(relevances, dtype=float)[:k]
    if rel.size == 0:
        return 0.0
    discounts = np.log2(np.arange(2, rel.size + 2))   # log2(i+1) for i=1..n
    return float(np.sum((np.power(2.0, rel) - 1.0) / discounts))


def ndcg_at_k(relevances: np.ndarray, k: int) -> float:
    rel = np.asarray(relevances, dtype=float)
    actual = dcg_at_k(rel, k)
    ideal = dcg_at_k(np.sort(rel)[::-1], k)
    return float(actual / ideal) if ideal > 0 else 0.0


def precision_at_k(relevances: np.ndarray, k: int, threshold: float = 1.0) -> float:
    rel = np.asarray(relevances, dtype=float)[:k]
    if rel.size == 0:
        return 0.0
    return float(np.mean(rel >= threshold))


def recall_at_k(relevances: np.ndarray, k: int, threshold: float = 1.0) -> float:
    rel = np.asarray(relevances, dtype=float)
    total_relevant = int(np.sum(rel >= threshold))
    if total_relevant == 0:
        return 0.0
    return float(np.sum(rel[:k] >= threshold) / total_relevant)


def reciprocal_rank(relevances: np.ndarray, threshold: float = 1.0) -> float:
    rel = np.asarray(relevances, dtype=float)
    hits = np.nonzero(rel >= threshold)[0]
    return float(1.0 / (hits[0] + 1)) if hits.size else 0.0


def average_precision(relevances: np.ndarray, threshold: float = 1.0) -> float:

    rel = np.asarray(relevances, dtype=float)
    is_rel = rel >= threshold
    if not is_rel.any():
        return 0.0
    precisions = np.cumsum(is_rel) / np.arange(1, rel.size + 1)
    return float(np.sum(precisions * is_rel) / np.sum(is_rel))


# ----------------------------------------------------------------------
# Correlation (for the continuous quality score)
# ----------------------------------------------------------------------
def spearman(predicted: np.ndarray, actual: np.ndarray) -> float:
    """Rank correlation"""
    if len(predicted) < 3:
        return float("nan")
    rho, _ = spearmanr(predicted, actual)
    return float(rho) if not np.isnan(rho) else 0.0


# ----------------------------------------------------------------------
# Uncertainty — the part most student projects omit
# ----------------------------------------------------------------------
def bootstrap_ci(
    per_query_scores: list[float],
    n_resamples: int = 2000,
    confidence: float = 0.95,
    seed: int = 42,
) -> tuple[float, float, float]:

    scores = np.asarray(per_query_scores, dtype=float)
    if scores.size == 0:
        return 0.0, 0.0, 0.0
    if scores.size == 1:
        v = float(scores[0])
        return v, v, v

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, scores.size, size=(n_resamples, scores.size))
    means = scores[idx].mean(axis=1)

    alpha = (1.0 - confidence) / 2.0
    return (
        float(scores.mean()),
        float(np.quantile(means, alpha)),
        float(np.quantile(means, 1.0 - alpha)),
    )


def paired_bootstrap_pvalue(
    scores_a: list[float],
    scores_b: list[float],
    n_resamples: int = 2000,
    seed: int = 42,
) -> float:

    a = np.asarray(scores_a, dtype=float)
    b = np.asarray(scores_b, dtype=float)
    if a.size != b.size or a.size < 2:
        return float("nan")

    observed = a.mean() - b.mean()
    diffs = a - b
    centred = diffs - diffs.mean()          # impose the null hypothesis

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, diffs.size, size=(n_resamples, diffs.size))
    null_dist = centred[idx].mean(axis=1)

    p = float(np.mean(np.abs(null_dist) >= abs(observed)))
    return max(p, 1.0 / n_resamples)        # never report p = 0
