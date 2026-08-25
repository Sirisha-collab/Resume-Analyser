"""
Per-query failure analysis.

The harness tells you a system scored 0.79. This tells you WHICH queries
dragged it down and WHY — which is the difference between a number and
something you can act on.

Error taxonomy:
  no_relevant      Nothing relevant exists in the pool. The query is
                   unanswerable; this is a LABEL problem, not a model problem.
  distractor_top   An irrelevant resume was ranked #1. The model is being
                   fooled by something — usually shared generic vocabulary.
  buried           Relevant resumes exist but sit below k. Classic recall
                   failure; the signal is too weak to surface them.
  partial          Some relevant surfaced, ordering imperfect. Normal.
  ok               Strong result.
"""
from __future__ import annotations

import numpy as np

from .metrics import ndcg_at_k


def classify(ranked_rel: np.ndarray, k: int, threshold: float = 1.0) -> str:
    total_rel = int(np.sum(ranked_rel >= threshold))
    if total_rel == 0:
        return "no_relevant"
    top = ranked_rel[:k]
    in_top = int(np.sum(top >= threshold))
    if ranked_rel[0] < threshold:
        return "distractor_top"
    if in_top == 0:
        return "buried"
    score = ndcg_at_k(ranked_rel, k)
    return "ok" if score >= 0.8 else "partial"


def diagnose(dataset, scorer, k: int = 5, top_n_worst: int = 5,
             rel_threshold: float = 1.0) -> dict:
    """Run one scorer and return a per-query breakdown."""
    resume_texts = [r.text for r in dataset.resumes]
    resume_ids = [r.resume_id for r in dataset.resumes]
    scorer.fit(resume_texts)

    rows = []
    for job in dataset.jobs:
        scores = np.asarray(scorer.score(job.text, resume_texts), dtype=float)
        order = sorted(range(len(scores)), key=lambda i: (-scores[i], resume_ids[i]))
        ranked_rel = np.array(
            [dataset.relevance(job.job_id, resume_ids[i]) for i in order], dtype=float
        )
        rows.append({
            "job_id": job.job_id,
            "title": (getattr(job, "title", "") or job.job_id)[:34],
            "ndcg": ndcg_at_k(ranked_rel, k),
            "n_relevant": int(np.sum(ranked_rel >= rel_threshold)),
            "top1_id": resume_ids[order[0]],
            "top1_rel": float(ranked_rel[0]),
            "failure": classify(ranked_rel, k, rel_threshold),
            "top_ids": [resume_ids[i] for i in order[:k]],
        })

    rows.sort(key=lambda r: r["ndcg"])
    return {
        "scorer": scorer.name,
        "per_query": rows,
        "worst": rows[:top_n_worst],
        "taxonomy": _tally([r["failure"] for r in rows]),
    }


def _tally(labels: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for l in labels:
        out[l] = out.get(l, 0) + 1
    return out


HINTS = {
    "no_relevant": "Label problem — this query has no relevant resume. "
                   "Either add one or drop the query.",
    "distractor_top": "An irrelevant resume ranked #1. Usually shared generic "
                      "wording. Check what terms it has in common with the JD.",
    "buried": "Relevant resumes exist but rank below k. Recall failure — the "
              "matching signal is too weak.",
    "partial": "Right documents, imperfect order. Usually acceptable.",
    "ok": "",
}


def print_report(diag: dict, k: int = 5) -> None:
    print(f"\n  FAILURE ANALYSIS — {diag['scorer']}")
    print("  " + "-" * 66)

    tax = diag["taxonomy"]
    total = sum(tax.values())
    print("  Query outcomes:")
    for label in ("ok", "partial", "buried", "distractor_top", "no_relevant"):
        n = tax.get(label, 0)
        if n:
            bar = "#" * int(28 * n / max(total, 1))
            print(f"    {label:<16} {n:>3} {bar}")

    print(f"\n  Worst {len(diag['worst'])} queries:")
    print(f"    {'nDCG@'+str(k):<8} {'#rel':<5} {'failure':<15} query")
    for r in diag["worst"]:
        print(f"    {r['ndcg']:<8.3f} {r['n_relevant']:<5} "
              f"{r['failure']:<15} {r['title']}")

    problem = [l for l in ("no_relevant", "distractor_top", "buried")
               if tax.get(l, 0) > 0]
    if problem:
        print("\n  What to do:")
        for l in problem:
            print(f"    [{l}] {HINTS[l]}")
    print("  " + "-" * 66)
