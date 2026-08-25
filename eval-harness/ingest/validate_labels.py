#!/usr/bin/env python3
"""
Validate automated labels against a human-labelled sample.

    python -m ingest.validate_labels --data data/real \
        --auto qrels.csv --human qrels_human_sample.csv

WHY THIS EXISTS
    Automated labels are only as trustworthy as their agreement with human
    judgement. Without this step, "I used an LLM to label" is an assertion.
    With it, you can say "my automated labels agree with human judgement at
    kappa = 0.74 on a 40-pair sample" — which is a defensible claim.

    This is the difference between an examiner nodding and an examiner
    asking a question you cannot answer.

HOW MUCH HUMAN LABELLING DO YOU NEED?
    Not much. 30-50 pairs is enough to estimate agreement. You label a
    random sample by hand ONCE, then validate every future automated run
    against it.
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import cohen_kappa_score, confusion_matrix


def read_qrels(path: Path) -> dict[tuple[str, str], int]:
    out = {}
    with path.open(encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            try:
                out[(row["job_id"].strip(), row["resume_id"].strip())] = int(
                    float(row["relevance"])
                )
            except (ValueError, KeyError):
                continue
    return out


def interpret_kappa(k: float) -> str:
    # Landis & Koch (1977) benchmarks
    if k < 0.0:   return "worse than chance — something is wrong"
    if k < 0.20:  return "slight — labels are not trustworthy"
    if k < 0.40:  return "fair — weak; report as a limitation"
    if k < 0.60:  return "moderate — usable with caveats"
    if k < 0.80:  return "substantial — defensible"
    return "almost perfect — strong"


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate automated labels vs human")
    ap.add_argument("--data", required=True)
    ap.add_argument("--auto", default="qrels.csv")
    ap.add_argument("--human", required=True,
                    help="hand-labelled sample (same 3-column format)")
    ap.add_argument("--make-sample", type=int, default=0,
                    help="instead of validating, emit N random pairs to hand-label")
    a = ap.parse_args()

    d = Path(a.data)

    # -------- optional: generate the sample to label --------
    if a.make_sample:
        import json
        resumes = [json.loads(l) for l in (d / "resumes.jsonl").read_text().splitlines() if l.strip()]
        jobs = [json.loads(l) for l in (d / "jobs.jsonl").read_text().splitlines() if l.strip()]
        rng = random.Random(42)
        pairs = [(j["job_id"], r["resume_id"], j.get("title", ""), r.get("source_file", ""),
                  " ".join(r["text"].split())[:150])
                 for j in jobs for r in resumes]
        rng.shuffle(pairs)
        out = d / "qrels_human_sample_TO_LABEL.csv"
        with out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["job_id", "resume_id", "relevance", "job_title",
                        "resume_file", "snippet"])
            for p in pairs[:a.make_sample]:
                w.writerow([p[0], p[1], "", p[2], p[3], p[4]])
        print(f"\n  {a.make_sample} random pairs -> {out}")
        print("  Label the 'relevance' column by hand (0-3), save, then re-run")
        print("  this command with --human pointing at it.\n")
        print("  IMPORTANT: label these WITHOUT looking at the automated labels,")
        print("  or your agreement number is meaningless.\n")
        return 0

    # -------- validate --------
    auto_path, human_path = d / a.auto, Path(a.human)
    if not human_path.exists():
        human_path = d / a.human
    if not human_path.exists():
        print(f"Human labels not found: {a.human}", file=sys.stderr)
        print(f"Generate a sample first:\n"
              f"  python -m ingest.validate_labels --data {a.data} "
              f"--human x --make-sample 40", file=sys.stderr)
        return 1

    auto = read_qrels(auto_path)
    human = read_qrels(human_path)

    # Unjudged = 0 on BOTH sides, so a pair the automation omitted but a human
    # graded 3 correctly counts as a disagreement.
    keys = set(human)
    y_human = np.array([human[k] for k in keys])
    y_auto = np.array([auto.get(k, 0) for k in keys])

    if len(keys) < 10:
        print(f"  Only {len(keys)} overlapping pairs — too few to estimate "
              "agreement. Label at least 30.", file=sys.stderr)
        return 1

    exact = float(np.mean(y_human == y_auto))
    within1 = float(np.mean(np.abs(y_human - y_auto) <= 1))
    # Quadratic weights: being off by 3 is much worse than off by 1
    kappa = cohen_kappa_score(y_human, y_auto, weights="quadratic")
    # Binary view: relevant vs not — often what actually matters for ranking
    kappa_bin = cohen_kappa_score(y_human >= 1, y_auto >= 1)

    print(f"\n  Compared {len(keys)} pairs")
    print("  " + "-" * 58)
    print(f"  Exact agreement        : {exact*100:.1f}%")
    print(f"  Within +/-1 grade      : {within1*100:.1f}%")
    print(f"  Cohen's kappa (graded) : {kappa:.3f}  <- {interpret_kappa(kappa)}")
    print(f"  Cohen's kappa (binary) : {kappa_bin:.3f}  <- {interpret_kappa(kappa_bin)}")
    print("  " + "-" * 58)

    labels = sorted(set(y_human) | set(y_auto))
    cm = confusion_matrix(y_human, y_auto, labels=labels)
    print("\n  Confusion (rows = human, cols = automated)")
    print("        " + "".join(f"{c:>6}" for c in labels))
    for i, r in enumerate(labels):
        print(f"    {r:>3} " + "".join(f"{v:>6}" for v in cm[i]))

    # Directional bias — the most actionable diagnostic
    diff = y_auto.astype(int) - y_human.astype(int)
    over, under = int(np.sum(diff > 0)), int(np.sum(diff < 0))
    print(f"\n  Automation over-graded {over}, under-graded {under}")
    if over > 2 * max(under, 1):
        print("  -> Automation is too GENEROUS. Raise your thresholds;")
        print("     over-labelling is what makes Random score high.")
    elif under > 2 * max(over, 1):
        print("  -> Automation is too STRICT. Lower thresholds or widen")
        print("     your skill vocabulary.")

    print("\n  HOW TO REPORT THIS")
    if kappa >= 0.60:
        print(f'    "Labels were generated automatically and validated against')
        print(f'     {len(keys)} hand-labelled pairs (quadratic kappa = {kappa:.2f},')
        print(f'     {interpret_kappa(kappa).split(" —")[0]} agreement)."')
    else:
        print(f"    kappa = {kappa:.2f} is too low to present as reliable.")
        print("    Either improve the labeller or fall back to hand-labelling")
        print("    a smaller set. Do not quote automated results at this level.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
