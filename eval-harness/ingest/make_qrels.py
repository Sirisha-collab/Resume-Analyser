#!/usr/bin/env python3
"""
Create relevance labels (qrels) — the one thing your existing files don't contain.

Three modes:

  --mode proxy      Auto-label from category folders. Fast, weak, honest.
  --mode worksheet  Emit a CSV for a human to fill in. Slow, credible.
  --mode pooled     Emit a worksheet containing only the top-K candidates
                    retrieved by a cheap method (standard IR practice —
                    you can't hand-label 100x20 pairs, but you can label
                    the 200 that any system might plausibly rank highly).

    python -m ingest.make_qrels --data data/real --mode proxy
    python -m ingest.make_qrels --data data/real --mode pooled --pool-k 10
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


# ----------------------------------------------------------------------
def mode_proxy(resumes, jobs, related: dict, out: Path) -> None:
    """Label by category match. Graded: 3 = same, 1 = related, 0 = other."""
    cats_r = {r["category"] for r in resumes if r.get("category")}
    cats_j = {j["category"] for j in jobs if j.get("category")}
    if not cats_r or not cats_j:
        raise SystemExit(
            "Proxy mode needs category labels on BOTH resumes and jobs.\n"
            "Organise files into per-role subfolders and re-run build_dataset,\n"
            "or use --mode worksheet / --mode pooled instead."
        )
    overlap = cats_r & cats_j
    if not overlap:
        raise SystemExit(
            f"No shared categories.\n  resumes: {sorted(cats_r)}\n  jobs: {sorted(cats_j)}\n"
            "Folder names must match between the two directories."
        )

    rows = []
    for j in jobs:
        for r in resumes:
            if not j.get("category") or not r.get("category"):
                continue
            if r["category"] == j["category"]:
                rel = 3
            else:
                rel = related.get(f"{r['category']}|{j['category']}", 0)
            if rel:
                rows.append((j["job_id"], r["resume_id"], rel))

    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["job_id", "resume_id", "relevance"])
        w.writerows(rows)

    print(f"\n  wrote {len(rows)} proxy judgements -> {out}")
    print(f"  categories used: {sorted(overlap)}")
    print("\n  ⚠️  These are PROXY labels. They measure category alignment,")
    print("      NOT genuine hiring fit. When you quote results, run with:")
    print('      --label-source "proxy (category match)"')
    print("      so the report auto-flags the limitation.\n")


# ----------------------------------------------------------------------
def mode_worksheet(resumes, jobs, out: Path, pool: dict | None, k: int) -> None:
    """Emit a CSV for a human to fill in the relevance column."""
    rows = []
    for j in jobs:
        candidates = pool[j["job_id"]] if pool else [r["resume_id"] for r in resumes]
        by_id = {r["resume_id"]: r for r in resumes}
        for rid in candidates[:k] if pool else candidates:
            r = by_id[rid]
            rows.append({
                "job_id": j["job_id"],
                "resume_id": rid,
                "relevance": "",                      # <- human fills this
                "job_title": j.get("title", "")[:60],
                "resume_file": r.get("source_file", "")[:40],
                "resume_snippet": " ".join(r["text"].split())[:160],
            })

    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"\n  wrote {len(rows)} rows to label -> {out}")
    print("\n  HOW TO LABEL — use a consistent rubric:")
    print("      3 = strong match, would shortlist")
    print("      2 = partial match, missing some requirements")
    print("      1 = weak / adjacent domain")
    print("      0 = not relevant")
    print("\n  For credibility, have a SECOND person label ~20% independently")
    print("  and report Cohen's kappa. An examiner asking 'how do you know")
    print("  your labels are reliable?' wants exactly that number.")
    print(f"\n  When done, save the filled file as qrels.csv (keep only the")
    print("  job_id, resume_id, relevance columns — extras are ignored).\n")


def build_pool(resumes, jobs, k: int) -> dict:
    """Pooling: shortlist candidates with TF-IDF so humans label a feasible subset.

    This is standard IR practice (TREC does it). You lose recall on documents
    no method retrieves, but labelling every pair is otherwise impossible.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    texts = [r["text"] for r in resumes]
    ids = [r["resume_id"] for r in resumes]
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
    M = vec.fit_transform(texts)

    pool = {}
    for j in jobs:
        sims = cosine_similarity(vec.transform([j["text"]]), M)[0]
        order = sorted(range(len(ids)), key=lambda i: -sims[i])
        pool[j["job_id"]] = [ids[i] for i in order[:k]]
    return pool


# ----------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Create relevance judgements")
    ap.add_argument("--data", required=True, help="dataset dir with resumes.jsonl / jobs.jsonl")
    ap.add_argument("--mode", choices=["proxy", "worksheet", "pooled"], default="proxy")
    ap.add_argument("--pool-k", type=int, default=10, help="candidates per job in pooled mode")
    ap.add_argument("--related", default="",
                    help='optional graded pairs, e.g. "ml_engineer|data_analyst=1,..."')
    a = ap.parse_args()

    d = Path(a.data)
    resumes = load_jsonl(d / "resumes.jsonl")
    jobs = load_jsonl(d / "jobs.jsonl")
    print(f"  loaded {len(resumes)} resumes, {len(jobs)} jobs")

    related = {}
    for pair in filter(None, a.related.split(",")):
        key, _, val = pair.partition("=")
        related[key.strip()] = int(val)

    if a.mode == "proxy":
        mode_proxy(resumes, jobs, related, d / "qrels.csv")
    elif a.mode == "worksheet":
        mode_worksheet(resumes, jobs, d / "qrels_TO_LABEL.csv", None, 0)
    else:
        pool = build_pool(resumes, jobs, a.pool_k)
        mode_worksheet(resumes, jobs, d / "qrels_TO_LABEL.csv", pool, a.pool_k)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
