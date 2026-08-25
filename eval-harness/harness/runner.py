"""
Evaluation runner.

For each job (query) it ranks the full resume pool, looks up graded relevance,
and computes per-query metrics. Per-query values are retained (not just means)
because bootstrap CIs and paired significance tests need them.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from .data import Dataset
from .metrics import (
    average_precision,
    bootstrap_ci,
    ndcg_at_k,
    paired_bootstrap_pvalue,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


@dataclass
class SystemResult:
    name: str
    per_query: dict[str, list[float]] = field(default_factory=dict)
    latency_ms_per_query: float = 0.0

    def mean(self, metric: str) -> float:
        vals = self.per_query.get(metric, [])
        return float(np.mean(vals)) if vals else 0.0

    def ci(self, metric: str, seed: int = 42) -> tuple[float, float, float]:
        return bootstrap_ci(self.per_query.get(metric, []), seed=seed)


class Evaluator:
    def __init__(self, dataset: Dataset, k_values: tuple[int, ...] = (1, 3, 5, 10),
                 rel_threshold: float = 1.0, seed: int = 42):
        self.dataset = dataset
        self.k_values = k_values
        self.rel_threshold = rel_threshold
        self.seed = seed
        self.warnings: list[str] = []
        self._sanity_check()

    # ------------------------------------------------------------------
    def _sanity_check(self) -> None:
        """Detect evaluations that CANNOT produce a meaningful result.

        A ranking metric needs something to rank. If the pool is one
        document, or every document is relevant, every system scores
        identically and the numbers are meaningless — even though the
        harness runs happily and emits a clean-looking report.

        These conditions are silent killers, so we surface them loudly.
        """
        ds = self.dataset
        n_res, n_jobs = len(ds.resumes), len(ds.jobs)

        if n_res < 2:
            self.warnings.append(
                f"FATAL: test pool has {n_res} resume(s). Ranking needs at least 2 "
                "documents — with one, every system produces the same order and "
                "every metric is 1.0 regardless of quality."
            )
        elif n_res < 10:
            self.warnings.append(
                f"Test pool is only {n_res} resumes. Ranking metrics are unstable "
                "below ~10 and nDCG@10 is not meaningful. Aim for 30+."
            )

        if n_jobs < 5:
            self.warnings.append(
                f"Only {n_jobs} queries. Confidence intervals will be very wide and "
                "no difference between systems can reach significance. Aim for 10-15+."
            )

        # Are all documents relevant to every query? Then there is nothing to separate.
        resume_ids = [r.resume_id for r in ds.resumes]
        degenerate = []
        for job in ds.jobs:
            rels = [ds.relevance(job.job_id, rid) for rid in resume_ids]
            n_rel = sum(1 for r in rels if r >= self.rel_threshold)
            if n_rel == len(rels) and len(rels) > 0:
                degenerate.append(job.job_id)
        if degenerate:
            self.warnings.append(
                f"{len(degenerate)}/{n_jobs} queries have EVERY resume marked relevant. "
                "There is no wrong answer to rank down, so all systems score 1.0. "
                "Relevance labels must discriminate — most resumes should be 0 for "
                "a given job."
            )

        # Relevance density is the root cause behind most inflated floors.
        judged = sum(
            1 for job in ds.jobs for rid in resume_ids
            if ds.relevance(job.job_id, rid) >= self.rel_threshold
        )
        total_pairs = max(n_jobs * n_res, 1)
        density = judged / total_pairs
        if density > 0.5:
            self.warnings.append(
                f"Relevance density is {density*100:.0f}% ({judged}/{total_pairs} pairs "
                "relevant). Ranking needs mostly-irrelevant documents; aim for "
                "10-35%. At this density a random ranker scores highly and no "
                "system can be distinguished."
            )

        # Largest k must be reachable
        max_k = max(self.k_values)
        if n_res < max_k:
            self.warnings.append(
                f"k={max_k} exceeds pool size ({n_res}); nDCG@{max_k} is really "
                f"nDCG@{n_res}. Use --k-values to match your pool."
            )

    def report_warnings(self) -> None:
        if not self.warnings:
            return
        print("\n  " + "=" * 68)
        print("  EVALUATION SANITY WARNINGS")
        print("  " + "=" * 68)
        for w in self.warnings:
            prefix = "  [FATAL] " if w.startswith("FATAL") else "  [WARN]  "
            body = w.replace("FATAL: ", "")
            print(f"{prefix}{body}")
        print("  " + "=" * 68)
        print("  If Random scores near the top, the evaluation is broken,")
        print("  not the model. Fix the data before quoting any number.")
        print("  " + "=" * 68 + "\n")


    # ------------------------------------------------------------------
    def evaluate(self, scorer, fit_corpus: list[str] | None = None) -> SystemResult:
        ds = self.dataset
        resume_texts = [r.text for r in ds.resumes]
        resume_ids = [r.resume_id for r in ds.resumes]

        # Fit on the TRAINING corpus only (leakage guard)
        scorer.fit(fit_corpus if fit_corpus is not None else resume_texts)

        result = SystemResult(name=scorer.name)
        metrics_acc: dict[str, list[float]] = {}
        total_time = 0.0

        for job in ds.jobs:
            t0 = time.perf_counter()
            scores = np.asarray(scorer.score(job.text, resume_texts), dtype=float)
            total_time += time.perf_counter() - t0

            if scores.shape[0] != len(resume_ids):
                raise ValueError(
                    f"{scorer.name} returned {scores.shape[0]} scores "
                    f"for {len(resume_ids)} resumes"
                )

            # Deterministic tie-breaking: stable sort on (-score, resume_id).
            # Without this, ties resolve by array order and results aren't
            # reproducible across runs or machines.
            order = sorted(
                range(len(scores)), key=lambda i: (-scores[i], resume_ids[i])
            )
            ranked_rel = np.array(
                [ds.relevance(job.job_id, resume_ids[i]) for i in order], dtype=float
            )

            for k in self.k_values:
                metrics_acc.setdefault(f"nDCG@{k}", []).append(ndcg_at_k(ranked_rel, k))
                metrics_acc.setdefault(f"P@{k}", []).append(
                    precision_at_k(ranked_rel, k, self.rel_threshold))
                metrics_acc.setdefault(f"Recall@{k}", []).append(
                    recall_at_k(ranked_rel, k, self.rel_threshold))
            metrics_acc.setdefault("MRR", []).append(
                reciprocal_rank(ranked_rel, self.rel_threshold))
            metrics_acc.setdefault("MAP", []).append(
                average_precision(ranked_rel, self.rel_threshold))

        result.per_query = metrics_acc
        result.latency_ms_per_query = (total_time / max(len(ds.jobs), 1)) * 1000
        return result

    # ------------------------------------------------------------------
    def check_random_tie(self, results: list[SystemResult], metric: str) -> str | None:
        """The single most important post-run check.

        If a random-number generator matches your best system, the evaluation
        is not measuring anything. Better to be told bluntly than to publish it.
        """
        rand = next((r for r in results if "Random" in r.name), None)
        if rand is None or len(results) < 2:
            return None
        best_other = max((r for r in results if r is not rand),
                         key=lambda r: r.mean(metric))
        rand_score = rand.mean(metric)
        best_score = best_other.mean(metric)

        if rand_score >= best_score - 1e-9:
            return (
                f"Random scored {rand_score:.3f} vs best system {best_score:.3f} "
                f"on {metric}. The evaluation is BROKEN — a coin flip is doing as "
                "well as your model. Almost always: too few documents, or labels "
                "that don't discriminate."
            )
        if rand_score > 0.5:
            return (
                f"Random scored {rand_score:.3f} on {metric} — implausibly high "
                "(a healthy floor is ~0.25-0.35). Your best system is "
                f"{best_score:.3f}, so the usable spread is only "
                f"{best_score - rand_score:.3f}. Too many documents are labelled "
                "relevant, so there is little to rank down. Differences between "
                "systems in this range are not trustworthy."
            )
        return None

    def compare(self, results: list[SystemResult], metric: str,
                baseline_name: str | None = None) -> dict[str, float]:
        """Paired bootstrap p-value of every system against the baseline.

        Answers the question that actually matters: is the improvement real,
        or is it noise from a small evaluation set?
        """
        if not results:
            return {}
        baseline = next(
            (r for r in results if r.name == baseline_name), results[0]
        )
        out = {}
        for r in results:
            if r.name == baseline.name:
                continue
            out[r.name] = paired_bootstrap_pvalue(
                r.per_query.get(metric, []),
                baseline.per_query.get(metric, []),
                seed=self.seed,
            )
        return out
