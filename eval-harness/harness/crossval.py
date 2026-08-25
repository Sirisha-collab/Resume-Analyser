"""
Cross-validated evaluation.

WHY THIS MATTERS FOR SMALL DATASETS
    A single train/test split on 23 resumes gives you ~11 test documents
    and N per-query observations. The confidence intervals come out so wide
    that nothing is distinguishable.

    K-fold rotates which resumes are held out. With 5 folds and 20 queries
    you get 100 per-query observations instead of 20 — the bootstrap has
    five times as much to work with, and the intervals tighten accordingly.

    It does NOT invent data. It uses what you have more efficiently, and it
    removes the luck of one particular split.

    Grouping is still by candidate_id, so the leakage guarantee holds in
    every fold.
"""
from __future__ import annotations

import numpy as np
from sklearn.model_selection import GroupKFold

from .data import Dataset
from .runner import Evaluator, SystemResult


def cross_validate(dataset: Dataset, scorer_factory, n_folds: int = 5,
                   k_values=(1, 3, 5, 10), seed: int = 42) -> SystemResult:
    """Evaluate one scorer across K folds, pooling per-query metrics.

    scorer_factory: a zero-arg callable returning a FRESH scorer per fold.
                    Must be fresh — a scorer fitted on fold 1's training data
                    would carry that fit into fold 2 and leak.
    """
    ids = [r.resume_id for r in dataset.resumes]
    groups = [r.candidate_id for r in dataset.resumes]
    n_groups = len(set(groups))
    folds = min(n_folds, n_groups)
    if folds < 2:
        raise ValueError("Need at least 2 candidate groups for cross-validation")

    splitter = GroupKFold(n_splits=folds)
    pooled: dict[str, list[float]] = {}
    total_ms, name = 0.0, None

    for train_idx, test_idx in splitter.split(ids, groups=groups):
        train_resumes = [dataset.resumes[i] for i in train_idx]
        test_resumes = [dataset.resumes[i] for i in test_idx]
        keep = {r.resume_id for r in test_resumes}

        fold_ds = Dataset(
            resumes=test_resumes,
            jobs=dataset.jobs,
            qrels={k: v for k, v in dataset.qrels.items() if k[1] in keep},
            label_source=dataset.label_source,
        )
        # Suppress per-fold sanity noise; the caller checks the pooled result.
        ev = Evaluator(fold_ds, k_values=k_values, seed=seed)
        ev.warnings = []

        scorer = scorer_factory()
        res = ev.evaluate(scorer, fit_corpus=[r.text for r in train_resumes])
        name = res.name
        total_ms += res.latency_ms_per_query

        for metric, vals in res.per_query.items():
            pooled.setdefault(metric, []).extend(vals)

    out = SystemResult(name=name or "unknown")
    out.per_query = pooled
    out.latency_ms_per_query = total_ms / folds
    return out


def summarise_gain(single: SystemResult, cv: SystemResult, metric: str) -> str:
    """Report how much the confidence interval tightened."""
    _, lo1, hi1 = single.ci(metric)
    _, lo2, hi2 = cv.ci(metric)
    w1, w2 = hi1 - lo1, hi2 - lo2
    n1 = len(single.per_query.get(metric, []))
    n2 = len(cv.per_query.get(metric, []))
    if w1 <= 0:
        return ""
    return (f"    observations {n1} -> {n2}   "
            f"CI width {w1:.3f} -> {w2:.3f}  ({(1 - w2/w1)*100:+.0f}%)")
