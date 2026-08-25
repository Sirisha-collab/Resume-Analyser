"""
Evaluation metrics for resume-to-job ranking.

Everything here is implemented from the definition rather than pulled from a
library, so you can defend each formula in a viva. Each function is unit-tested
in tests/test_metrics.py against hand-computed values.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr


# ----------------------------------------------------------------------
# Ranking metrics
# ----------------------------------------------------------------------
def dcg_at_k(relevances: np.ndarray, k: int) -> float:
    """Discounted Cumulative Gain.

        DCG@k = sum_{i=1..k} (2^rel_i - 1) / log2(i + 1)

    The 2^rel - 1 numerator is the standard "exponential gain" form: it
    rewards highly-relevant items disproportionately, which is what we want
    when a recruiter only reads the top few results.
    """
    rel = np.asarray(relevances, dtype=float)[:k]
    if rel.size == 0:
        return 0.0
    discounts = np.log2(np.arange(2, rel.size + 2))   # log2(i+1) for i=1..n
    return float(np.sum((np.power(2.0, rel) - 1.0) / discounts))


def ndcg_at_k(relevances: np.ndarray, k: int) -> float:
    """Normalised DCG: DCG achieved / DCG of the perfect ordering.

    Returns a value in [0, 1] that is comparable across queries with
    different numbers of relevant documents.
    """
    rel = np.asarray(relevances, dtype=float)
    actual = dcg_at_k(rel, k)
    ideal = dcg_at_k(np.sort(rel)[::-1], k)
    return float(actual / ideal) if ideal > 0 else 0.0


def precision_at_k(relevances: np.ndarray, k: int, threshold: float = 1.0) -> float:
    """Fraction of the top-k that are relevant (rel >= threshold)."""
    rel = np.asarray(relevances, dtype=float)[:k]
    if rel.size == 0:
        return 0.0
    return float(np.mean(rel >= threshold))


def recall_at_k(relevances: np.ndarray, k: int, threshold: float = 1.0) -> float:
    """Fraction of ALL relevant items that appear in the top k."""
    rel = np.asarray(relevances, dtype=float)
    total_relevant = int(np.sum(rel >= threshold))
    if total_relevant == 0:
        return 0.0
    return float(np.sum(rel[:k] >= threshold) / total_relevant)


def reciprocal_rank(relevances: np.ndarray, threshold: float = 1.0) -> float:
    """1 / rank of the first relevant item; 0 if none are relevant.

    Averaged over queries this is MRR. Useful when the user only cares about
    finding one good match quickly.
    """
    rel = np.asarray(relevances, dtype=float)
    hits = np.nonzero(rel >= threshold)[0]
    return float(1.0 / (hits[0] + 1)) if hits.size else 0.0


def average_precision(relevances: np.ndarray, threshold: float = 1.0) -> float:
    """Mean of precision@i taken at every rank i where a relevant item appears."""
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
    """Rank correlation.

    Chosen over RMSE deliberately: if human raters use a 1-5 scale and the
    model outputs 0-100, RMSE punishes a scale mismatch we don't care about.
    What matters is whether better resumes rank higher.
    """
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
    """Bootstrap confidence interval over per-query metric values.

    Why this matters: with 40 evaluation queries, a difference of 0.79 vs 0.82
    between two systems may be pure noise. Resampling the queries with
    replacement tells you whether the gap survives.

    Returns (mean, ci_low, ci_high).
    """
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
    """Two-sided paired bootstrap test: is system A genuinely better than B?

    Both systems are scored on the SAME queries, so we resample query indices
    once and apply them to both — that pairing removes query difficulty as a
    confound and gives far more power than comparing independent means.

    Returns an approximate p-value for H0: mean(A) == mean(B).
    """
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
