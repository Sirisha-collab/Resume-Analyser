#!/usr/bin/env python3
"""
Resume Analyser — evaluation harness CLI.

    python run_eval.py --data data/sample --out results/

Reproducibility: every run is seeded and the seed is recorded in the report.
Two runs with the same seed and data produce byte-identical metrics.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from harness.data import load_dataset, split_by_candidate
from harness.report import plot_comparison, write_csv, write_markdown
from harness.runner import Evaluator
from harness.scorers import (
    BM25Scorer,
    EmbeddingScorer,
    JaccardScorer,
    RandomScorer,
    SectionWeightedEmbeddingScorer,
    TfidfCosineScorer,
    embeddings_available,
)

import textwrap


def _wrap(text: str, width: int) -> list[str]:
    return textwrap.wrap(text, width)


BASELINE = "TF-IDF cosine"     # the bar a new system must clear


def build_scorers(seed: int, use_embeddings: bool) -> list:
    scorers = [
        RandomScorer(seed=seed),
        JaccardScorer(),
        BM25Scorer(),
        TfidfCosineScorer(),
    ]
    if use_embeddings:
        if embeddings_available():
            scorers += [EmbeddingScorer(), SectionWeightedEmbeddingScorer()]
        else:
            print(
                "  ! sentence-transformers not installed — skipping embedding scorers.\n"
                "    Install with: pip install sentence-transformers",
                file=sys.stderr,
            )
    return scorers


def build_scorer_factories(seed: int, use_embeddings: bool) -> list:
    """Zero-arg factories returning FRESH scorers.

    Cross-validation needs a new instance per fold — reusing a fitted scorer
    would carry fold 1's training fit into fold 2 and leak.
    """
    facs = [
        lambda: RandomScorer(seed=seed),
        lambda: JaccardScorer(),
        lambda: BM25Scorer(),
        lambda: TfidfCosineScorer(),
    ]
    if use_embeddings and embeddings_available():
        facs += [lambda: EmbeddingScorer(), lambda: SectionWeightedEmbeddingScorer()]
    return facs


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate Resume Analyser ranking quality")
    ap.add_argument("--data", default="data/sample", help="dataset directory")
    ap.add_argument("--out", default="results", help="output directory")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--test-size", type=float, default=0.2)
    ap.add_argument("--primary-metric", default="nDCG@5")
    ap.add_argument("--label-source", default="proxy (category match)",
                    help="How relevance was labelled — printed in the report")
    ap.add_argument("--no-embeddings", action="store_true",
                    help="Skip BERT scorers (fast lexical-only run)")
    ap.add_argument("--folds", type=int, default=0,
                    help="K-fold cross-validation instead of a single split. "
                         "Strongly recommended for small datasets — tightens CIs.")
    ap.add_argument("--diagnose", action="store_true",
                    help="Per-query failure analysis for the best system")
    args = ap.parse_args()

    data_dir = Path(args.data)
    if not data_dir.exists():
        print(f"Dataset not found: {data_dir}\n"
              f"Generate a sample with:  python -m harness.make_sample_data",
              file=sys.stderr)
        return 1

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- Load & split -------------------------------------------------
    dataset = load_dataset(data_dir, label_source=args.label_source)
    print(f"Loaded {dataset}")

    train, test = split_by_candidate(dataset, test_size=args.test_size, seed=args.seed)
    print(f"  train: {len(train.resumes)} resumes | test: {len(test.resumes)} resumes")
    print(f"  (split grouped by candidate_id — no candidate spans both sides)\n")

    # Fit corpus comes from TRAIN only. This is the leakage guard.
    fit_corpus = [r.text for r in train.resumes]

    # --- Evaluate on the TEST split -----------------------------------
    evaluator = Evaluator(test, k_values=(1, 3, 5, 10), seed=args.seed)
    evaluator.report_warnings()
    scorers = build_scorers(args.seed, use_embeddings=not args.no_embeddings)

    results = []
    if args.folds and args.folds > 1:
        from harness.crossval import cross_validate, summarise_gain
        print(f"  Cross-validating over {args.folds} folds "
              f"(grouped by candidate — leakage guard holds per fold)\n")
        factories = build_scorer_factories(args.seed,
                                           use_embeddings=not args.no_embeddings)
        for make in factories:
            probe = make()
            print(f"  evaluating: {probe.name} ...", end=" ", flush=True)
            single = evaluator.evaluate(make(), fit_corpus=fit_corpus)
            cv = cross_validate(dataset, make, n_folds=args.folds, seed=args.seed)
            results.append(cv)
            print(f"{args.primary_metric}={cv.mean(args.primary_metric):.3f} "
                  f"({cv.latency_ms_per_query:.1f} ms/query)")
            gain = summarise_gain(single, cv, args.primary_metric)
            if gain:
                print(gain)
    else:
        for scorer in scorers:
            print(f"  evaluating: {scorer.name} ...", end=" ", flush=True)
            res = evaluator.evaluate(scorer, fit_corpus=fit_corpus)
            results.append(res)
            print(f"{args.primary_metric}={res.mean(args.primary_metric):.3f} "
                  f"({res.latency_ms_per_query:.1f} ms/query)")

    # --- The single most important check ------------------------------
    tie = evaluator.check_random_tie(results, args.primary_metric)
    if tie:
        print("\n  " + "!" * 68)
        print("  RESULTS ARE NOT USABLE")
        print("  " + "!" * 68)
        for line in _wrap(tie, 66):
            print(f"  {line}")
        print("  " + "!" * 68)
        print("  Do NOT put these numbers in a report or slide.")
        print("  " + "!" * 68 + "\n")

    # --- Significance vs baseline -------------------------------------
    baseline = BASELINE if any(r.name == BASELINE for r in results) else results[0].name
    pvalues = evaluator.compare(results, args.primary_metric, baseline_name=baseline)

    # --- Per-query failure analysis -----------------------------------
    diag_data = None
    if args.diagnose:
        from harness.diagnose import diagnose, print_report
        best = max((r for r in results if "Random" not in r.name),
                   key=lambda r: r.mean(args.primary_metric))
        target = next((s for s in build_scorers(args.seed,
                                                use_embeddings=not args.no_embeddings)
                       if s.name == best.name), None)
        if target is not None:
            diag_data = diagnose(test, target, k=5)
            print_report(diag_data, k=5)

    # --- Report -------------------------------------------------------
    metrics = ["nDCG@5", "nDCG@10", "P@5", "Recall@10", "MRR", "MAP"]
    write_csv(results, metrics, out_dir / "results.csv")
    write_markdown(
        results, metrics, args.primary_metric, pvalues,
        dataset_repr=repr(test), label_source=args.label_source,
        path=out_dir / "report.md", baseline_name=baseline,
    )
    plot_comparison(results, args.primary_metric,
                    out_dir / "comparison.png", baseline_name=baseline)

    from harness.export_json import export_json
    export_json(
        results, args.primary_metric, baseline, pvalues,
        dataset_repr=repr(test), label_source=args.label_source,
        warnings=evaluator.warnings, alert=tie,
        out_path=out_dir / "dashboard.json",
        diag=diag_data, n_folds=args.folds, all_metrics=metrics,
    )

    from harness.dashboard import render_dashboard
    render_dashboard(
        results, args.primary_metric, baseline, pvalues,
        dataset_repr=repr(test), label_source=args.label_source,
        warnings=evaluator.warnings, alert=tie,
        out_path=out_dir / "dashboard.html",
        diag=diag_data, n_folds=args.folds,
    )

    print(f"\nWrote:\n  {out_dir/'dashboard.html'}   <- open in browser"
          f"\n  {out_dir/'dashboard.json'}   <- for the React dashboard"
          f"\n  {out_dir/'report.md'}\n  {out_dir/'results.csv'}"
          f"\n  {out_dir/'comparison.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
