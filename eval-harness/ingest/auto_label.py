#!/usr/bin/env python3
"""
Automatic relevance labelling — the system assigns the scores.

    python -m ingest.auto_label --data data/real
    python -m ingest.auto_label --data data/real --target-density 0.20

=======================================================================
HOW IT WORKS

  1. Build IDF statistics over your resume corpus.
  2. For each job, pull out its DISTINCTIVE terms — words rare in the
     corpus but present in the JD. Those are the real requirements.
     ("kubernetes" is distinctive; "communication" is not.)
  3. For each resume, compute IDF-weighted coverage of those terms.
  4. CALIBRATE thresholds so the label set hits a target density.

WHY CALIBRATION MATTERS
  Every failure you have hit came from labelling too many pairs relevant.
  Fixed thresholds cannot prevent that — a generous cutoff on an easy
  corpus marks everything relevant, and then a coin flip scores 0.8.
  Calibration makes that impossible: you declare the density you want and
  the labeller solves for the cutoffs from the actual score distribution.

NO FIXED VOCABULARY
  The previous version matched a hardcoded skill list and produced zero
  labels when your terms were not on it. This derives requirements from
  your own text, so it adapts to any domain.

INDEPENDENCE
  This is a lexical labeller, so it CORRELATES with keyword scorers
  (Jaccard, BM25, your ATS layer). Use it to judge your semantic/BERT
  layer; treat ATS-layer numbers from it with suspicion. For a fully
  independent signal use --strategy llm.
=======================================================================
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
from collections import Counter
from pathlib import Path

import numpy as np

TOKEN_RE = re.compile(r"[a-z][a-z0-9+#.\-/]{1,}")

STOPWORDS = {
    "the", "and", "for", "with", "you", "our", "will", "are", "who", "this", "that",
    "have", "has", "from", "your", "their", "they", "them", "was", "were", "been",
    "can", "all", "any", "one", "two", "new", "not", "but", "out", "use", "using",
    "work", "working", "team", "teams", "role", "roles", "years", "year", "job",
    "candidate", "candidates", "experience", "experienced", "strong", "excellent",
    "good", "great", "ability", "able", "skills", "skill", "knowledge",
    "understanding", "responsibilities", "requirements", "required", "preferred",
    "plus", "must", "should", "would", "looking", "seeking", "hiring", "join",
    "company", "business", "help", "support", "across", "within", "into", "also",
    "well", "including", "etc", "such", "other", "others", "more", "most", "own",
    "per", "via", "through", "summary", "education", "projects",
}

PHRASES = [
    "machine learning", "deep learning", "natural language processing",
    "computer vision", "power bi", "data science", "data analysis",
    "container orchestration", "relational database", "business intelligence",
    "data visualisation", "data visualization", "project management",
    "continuous integration", "test automation", "cloud computing",
]


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def tokenize(text: str) -> list[str]:
    t = text.lower()
    for ph in PHRASES:
        t = t.replace(ph, ph.replace(" ", "_"))
    return [w for w in TOKEN_RE.findall(t) if w not in STOPWORDS and len(w) > 2]


# ----------------------------------------------------------------------
def build_idf(docs: list[str]) -> dict[str, float]:
    """IDF over the resume corpus. High IDF = distinctive = a real requirement."""
    n = len(docs)
    df: Counter = Counter()
    for d in docs:
        df.update(set(tokenize(d)))
    return {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}


def job_requirements(job_text: str, idf: dict[str, float], top_n: int) -> dict[str, float]:
    """A job's most distinctive terms.

    Terms no resume mentions are dropped — they cannot discriminate.
    """
    counts = Counter(tokenize(job_text))
    scored = {t: idf[t] * (1 + math.log(c)) for t, c in counts.items() if t in idf}
    return dict(sorted(scored.items(), key=lambda kv: -kv[1])[:top_n])


def coverage(resume_text: str, reqs: dict[str, float]) -> float:
    """Fraction of the job's requirement WEIGHT present in the resume (0-1)."""
    if not reqs:
        return 0.0
    have = set(tokenize(resume_text))
    total = sum(reqs.values())
    return sum(w for t, w in reqs.items() if t in have) / total if total else 0.0


# ----------------------------------------------------------------------
def calibrate(scores: np.ndarray, target_density: float,
              tiers: tuple[float, float, float] = (0.25, 0.35, 0.40)):
    """Solve for grade cutoffs that produce the requested density.

    Rather than guessing a threshold, read the cutoffs off the observed
    score distribution. This is what makes runaway density impossible.
    """
    if scores.size == 0:
        return 1.0, 1.0, 1.0
    d = float(np.clip(target_density, 0.02, 0.9))
    f3, f2, _ = tiers
    p3 = 100 * (1 - d * f3)
    p2 = 100 * (1 - d * (f3 + tiers[1]))
    p1 = 100 * (1 - d)
    t3, t2, t1 = (float(np.percentile(scores, p)) for p in (p3, p2, p1))
    t2 = min(t2, t3)
    t1 = min(t1, t2)
    return t3, t2, t1


def grade(score: float, t3: float, t2: float, t1: float, floor: float) -> int:
    """Absolute floor beats percentile: near-zero overlap is 0 even if it is
    the best of a bad pool."""
    if score < floor:
        return 0
    if score >= t3:
        return 3
    if score >= t2:
        return 2
    if score >= t1:
        return 1
    return 0


# ----------------------------------------------------------------------
def label_lexical(resumes, jobs, target_density, floor, top_n, verbose,
                  strategy="hybrid", w_skill=0.6):
    """Score every (job, resume) pair, then calibrate cutoffs.

    strategy:
      skills  - YOUR TECH_SKILLS vocabulary only. Most domain-accurate,
                but CIRCULAR with your ATS/Jaccard scorer.
      idf     - corpus-derived distinctive terms. Independent of your
                vocabulary, but blind to synonyms.
      hybrid  - weighted blend (default). Keeps synonym handling while
                diluting the circularity, since the IDF half is derived
                from your corpus rather than your skill list.
    """
    from ingest import skills as SK

    idf = build_idf([r["text"] for r in resumes])
    matrix = np.zeros((len(jobs), len(resumes)))
    req_cache = {}

    for jx, j in enumerate(jobs):
        reqs = job_requirements(j["text"], idf, top_n)
        req_cache[j["job_id"]] = reqs
        for rx, r in enumerate(resumes):
            s_idf = coverage(r["text"], reqs)
            s_skill = SK.coverage(r["text"], j["text"])
            if strategy == "skills":
                matrix[jx, rx] = s_skill
            elif strategy == "idf":
                matrix[jx, rx] = s_idf
            else:
                matrix[jx, rx] = w_skill * s_skill + (1 - w_skill) * s_idf

    t3, t2, t1 = calibrate(matrix.flatten(), target_density)

    rows = []
    for jx, j in enumerate(jobs):
        for rx, r in enumerate(resumes):
            g = grade(matrix[jx, rx], t3, t2, t1, floor)
            if g:
                rows.append((j["job_id"], r["resume_id"], g))

    if verbose:
        print(f"\n  {SK.describe()}")
        print(f"  scoring strategy: {strategy}"
              + (f" (skill weight {w_skill})" if strategy == "hybrid" else ""))
        print("\n  Requirements extracted (sample):")
        for j in jobs[:3]:
            title = (j.get("title") or j["job_id"])[:30]
            jd_skills = sorted(SK.extract_skills(j["text"]))[:6]
            idf_terms = list(req_cache[j["job_id"]])[:6]
            print(f"    {title:<30} skills: {', '.join(jd_skills) or '(none)'}")
            print(f"    {'':<30} idf   : {', '.join(idf_terms)}")
        print(f"\n  Calibrated cutoffs:  3>={t3:.3f}   2>={t2:.3f}   1>={t1:.3f}"
              f"   (floor {floor})")
        print(f"  Score spread:        min={matrix.min():.3f}  "
              f"median={np.median(matrix):.3f}  max={matrix.max():.3f}")
    return rows


# ----------------------------------------------------------------------
JUDGE_PROMPT = """You are grading how well a candidate's resume matches a job description.

Rubric — use it EXACTLY:
3 = Strong match. Has most required skills and relevant experience. Would shortlist.
2 = Partial match. Has some required skills but clear gaps.
1 = Weak match. Adjacent domain or few overlapping skills.
0 = Not relevant. Different field entirely.

Grade ONLY on evidence present in the resume text. Do not infer skills that are
not stated. Do not reward confident writing or formatting. Most resumes should
score 0 or 1 for any given job — be strict.

JOB DESCRIPTION:
{job}

RESUME:
{resume}

Respond with ONLY a JSON object, no other text:
{{"relevance": <0-3>, "reason": "<one short sentence>"}}"""


def label_llm(resumes, jobs, model, cache_path, max_chars=3000):
    try:
        import anthropic
    except ImportError:
        raise SystemExit("pip install anthropic")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY")

    client = anthropic.Anthropic()
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    rows, calls = [], 0
    print(f"  grading {len(jobs)*len(resumes)} pairs (cached: {len(cache)})")

    for j in jobs:
        for r in resumes:
            key = f"{j['job_id']}|{r['resume_id']}"
            if key not in cache:
                resp = client.messages.create(
                    model=model, max_tokens=200, temperature=0,
                    messages=[{"role": "user", "content": JUDGE_PROMPT.format(
                        job=j["text"][:max_chars], resume=r["text"][:max_chars])}],
                )
                raw = "".join(b.text for b in resp.content if b.type == "text").strip()
                raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```")
                try:
                    cache[key] = json.loads(raw)
                except json.JSONDecodeError:
                    cache[key] = {"relevance": 0, "reason": "parse_error"}
                calls += 1
                if calls % 20 == 0:
                    cache_path.write_text(json.dumps(cache, indent=1))
                    print(f"    {calls} calls...")
            rel = int(cache[key].get("relevance", 0))
            if rel:
                rows.append((j["job_id"], r["resume_id"], rel))
    cache_path.write_text(json.dumps(cache, indent=1))
    print(f"  {calls} new API calls")
    return rows


# ----------------------------------------------------------------------
def summarise(rows, n_jobs, n_res) -> bool:
    dist = Counter(r[2] for r in rows)
    total = n_jobs * n_res
    judged = len(rows)
    density = judged / total if total else 0

    print(f"\n  judged {judged}/{total} pairs \u2014 density {density*100:.0f}%")
    for g in (3, 2, 1):
        print(f"    grade {g}: {dist.get(g, 0)}")
    print(f"    grade 0 (omitted): {total - judged}")

    per_job = Counter(r[0] for r in rows)
    saturated = [j for j, c in per_job.items() if c >= n_res]
    empty = n_jobs - len(per_job)

    ok = True
    if saturated:
        print(f"\n  \u26a0\ufe0f  {len(saturated)} job(s) have EVERY resume relevant "
              "\u2014 those queries cannot discriminate.")
        ok = False
    if empty:
        print(f"\n  \u26a0\ufe0f  {empty} job(s) have NO relevant resume "
              "\u2014 those queries score 0 for everyone.")
        ok = False
    if density > 0.45:
        print(f"\n  \u26a0\ufe0f  Density {density*100:.0f}% too high \u2014 re-run with "
              "--target-density 0.20")
        ok = False
    elif density < 0.05:
        print(f"\n  \u26a0\ufe0f  Density {density*100:.0f}% too sparse \u2014 re-run with "
              "--target-density 0.25")
        ok = False
    elif ok:
        print(f"\n  \u2705 Density {density*100:.0f}% is healthy (target 10-35%).")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="Let the system assign relevance scores")
    ap.add_argument("--data", required=True)
    ap.add_argument("--strategy", choices=["hybrid", "skills", "idf", "llm"],
                    default="hybrid",
                    help="hybrid=your skills + corpus IDF (default); "
                         "skills=TECH_SKILLS only (circular with ATS layer); "
                         "idf=corpus only; llm=independent judge")
    ap.add_argument("--skill-weight", type=float, default=0.6,
                    help="hybrid blend weight on TECH_SKILLS coverage")
    ap.add_argument("--target-density", type=float, default=0.25)
    ap.add_argument("--floor", type=float, default=0.08,
                    help="absolute min coverage to be relevant at all")
    ap.add_argument("--top-n", type=int, default=25,
                    help="distinctive terms defining a job's requirements")
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--out", default="qrels.csv")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    d = Path(a.data)
    resumes, jobs = load_jsonl(d / "resumes.jsonl"), load_jsonl(d / "jobs.jsonl")
    print(f"  {len(resumes)} resumes x {len(jobs)} jobs = {len(resumes)*len(jobs)} pairs")

    if a.strategy == "llm":
        rows = label_llm(resumes, jobs, a.model, d / "llm_judge_cache.json")
    else:
        rows = label_lexical(resumes, jobs, a.target_density, a.floor,
                             a.top_n, verbose=not a.quiet,
                             strategy=a.strategy, w_skill=a.skill_weight)
        if a.strategy == "skills":
            print("\n  \u26a0\ufe0f  CIRCULARITY: these labels come from the same "
                  "TECH_SKILLS vocabulary")
            print("      your ATS/Jaccard scorer uses. Results for that layer are")
            print("      not trustworthy. Use them to judge your BERT layer only.")

    if not rows:
        print("\n  No labels produced \u2014 lower --floor or raise --target-density.")
        return 1

    out = d / a.out
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["job_id", "resume_id", "relevance"])
        w.writerows(sorted(rows))

    healthy = summarise(rows, len(jobs), len(resumes))
    print(f"\n  -> {out}")
    print(f'\n  Run:  python run_eval.py --data {a.data} --out results '
          f'--label-source "{a.strategy} auto, density={a.target_density}"')
    print("  Then check: is Random below 0.4?\n" if healthy
          else "  Fix the warnings above first.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
