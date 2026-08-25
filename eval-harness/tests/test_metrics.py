"""
Tests for the metrics themselves.

An evaluation harness that isn't tested can silently report wrong numbers,
which is worse than having no harness. Expected values here are computed by
hand from the formulas.
"""
import math

import numpy as np
import pytest

from harness.metrics import (
    average_precision,
    bootstrap_ci,
    dcg_at_k,
    ndcg_at_k,
    paired_bootstrap_pvalue,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    spearman,
)


# ---------------------------------------------------------------- DCG
def test_dcg_hand_computed():
    # rel = [3, 2, 0]
    #   i=1: (2^3-1)/log2(2) = 7/1     = 7.0
    #   i=2: (2^2-1)/log2(3) = 3/1.585 = 1.8928
    #   i=3: (2^0-1)/log2(4) = 0/2     = 0.0
    expected = 7.0 + 3.0 / math.log2(3)
    assert dcg_at_k(np.array([3, 2, 0]), 3) == pytest.approx(expected, rel=1e-9)


def test_dcg_respects_k():
    assert dcg_at_k(np.array([3, 3, 3]), 1) == pytest.approx(7.0)


def test_dcg_empty_is_zero():
    assert dcg_at_k(np.array([]), 5) == 0.0


# --------------------------------------------------------------- nDCG
def test_ndcg_perfect_ranking_is_one():
    assert ndcg_at_k(np.array([3, 2, 1, 0]), 4) == pytest.approx(1.0)


def test_ndcg_worst_ranking_is_low():
    assert ndcg_at_k(np.array([0, 1, 2, 3]), 4) < 0.6


def test_ndcg_all_irrelevant_is_zero():
    assert ndcg_at_k(np.array([0, 0, 0]), 3) == 0.0


def test_ndcg_bounded():
    rng = np.random.default_rng(0)
    for _ in range(50):
        rel = rng.integers(0, 4, size=10)
        assert 0.0 <= ndcg_at_k(rel, 5) <= 1.0 + 1e-9


# ---------------------------------------------------- precision/recall
def test_precision_at_k():
    assert precision_at_k(np.array([3, 0, 2, 0, 1]), 5) == pytest.approx(0.6)


def test_precision_at_k_truncates():
    assert precision_at_k(np.array([3, 3, 0, 0]), 2) == pytest.approx(1.0)


def test_recall_at_k():
    # 4 relevant in total, 2 within the top 3
    assert recall_at_k(np.array([1, 0, 1, 1, 1]), 3) == pytest.approx(0.5)


def test_recall_no_relevant_is_zero():
    assert recall_at_k(np.array([0, 0]), 2) == 0.0


# ----------------------------------------------------------------- RR
def test_reciprocal_rank_first_position():
    assert reciprocal_rank(np.array([2, 0, 0])) == pytest.approx(1.0)


def test_reciprocal_rank_third_position():
    assert reciprocal_rank(np.array([0, 0, 1])) == pytest.approx(1 / 3)


def test_reciprocal_rank_none_relevant():
    assert reciprocal_rank(np.array([0, 0, 0])) == 0.0


# ---------------------------------------------------------------- MAP
def test_average_precision_hand_computed():
    # rel = [1, 0, 1]; precision at hits: 1/1 and 2/3 -> mean = 0.8333
    assert average_precision(np.array([1, 0, 1])) == pytest.approx((1.0 + 2 / 3) / 2)


# ----------------------------------------------------------- Spearman
def test_spearman_perfect_positive():
    assert spearman(np.array([1, 2, 3, 4]), np.array([10, 20, 30, 40])) == pytest.approx(1.0)


def test_spearman_perfect_negative():
    assert spearman(np.array([1, 2, 3, 4]), np.array([40, 30, 20, 10])) == pytest.approx(-1.0)


def test_spearman_is_scale_invariant():
    """The reason we use Spearman over RMSE: a 1-5 vs 0-100 scale mismatch
    must not be penalised."""
    human = np.array([1, 2, 3, 4, 5])
    model = np.array([20, 40, 60, 80, 100])
    assert spearman(model, human) == pytest.approx(1.0)


# ---------------------------------------------------------- bootstrap
def test_bootstrap_ci_brackets_mean():
    scores = [0.5, 0.6, 0.7, 0.8, 0.9]
    mean, lo, hi = bootstrap_ci(scores, n_resamples=1000, seed=1)
    assert mean == pytest.approx(0.7)
    assert lo <= mean <= hi


def test_bootstrap_ci_is_deterministic_with_seed():
    s = [0.1, 0.4, 0.9, 0.3]
    assert bootstrap_ci(s, seed=7) == bootstrap_ci(s, seed=7)


def test_bootstrap_ci_single_value():
    assert bootstrap_ci([0.42]) == (0.42, 0.42, 0.42)


def test_paired_bootstrap_detects_real_difference():
    a = [0.9] * 30
    b = [0.4] * 30
    assert paired_bootstrap_pvalue(a, b, seed=3) < 0.05


def test_paired_bootstrap_identical_systems_not_significant():
    rng = np.random.default_rng(11)
    vals = rng.random(40).tolist()
    assert paired_bootstrap_pvalue(vals, vals, seed=3) > 0.05


def test_paired_bootstrap_never_returns_zero():
    p = paired_bootstrap_pvalue([1.0] * 50, [0.0] * 50, n_resamples=500, seed=5)
    assert p > 0.0
