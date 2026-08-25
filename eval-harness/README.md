# Resume Analyser — Evaluation Harness

A reproducible harness for measuring how well Resume Analyser ranks resumes
against job descriptions, with baselines, ablations, and statistical
significance testing.

This exists to answer two interview questions properly:
**"What dataset did you evaluate on and how?"** and **"What metrics and baseline?"**

---

## Quick start

python -m ingest.build_dataset --resumes "D:\Docs Latest\A Masters Required doc\Projects\Resume Analyser\ResumeAnalysis_PY\Samples\Resumes" --jobs "D:\Docs Latest\A Masters Required doc\Projects\Resume Analyser\ResumeAnalysis_PY\Samples\Job Description" --out data/real
<!-- Previous commands:
python -m ingest.make_qrels --data data\real --mode worksheet
python run_eval.py --data data\real --out results_real --label-source "hand-labelled, n=12" -->

New: 
python -m ingest.auto_label --data data\real --target-density 0.22

python run_eval.py --data data\real --out results_real --test-size 0.5 --label-source "hybrid auto (TECH_SKILLS + IDF)"

```bash
pip install numpy pandas scikit-learn scipy matplotlib pytest
pip install sentence-transformers          # optional: enables the BERT scorers

python -m harness.make_sample_data          # writes data/sample/
python run_eval.py --data data/sample --out results --test-size 0.4
```

Outputs land in `results/`:

| File | Contents |
|---|---|
| `report.md` | Full results table, CIs, significance verdicts |
| `results.csv` | Machine-readable metrics |
| `comparison.png` | Bar chart with 95% CIs — drop straight into your slides |

Run the harness's own tests:

```bash
python -m pytest tests/ -q          # 24 tests, all metrics hand-verified
```

---

## ⚠️ The sample dataset is synthetic

`harness/make_sample_data.py` generates fake resumes so the plumbing runs out
of the box. **Numbers from it are not evidence about your model.** Replace it
with real data before quoting anything.

It is, however, deliberately built to be *hard*:

- Job descriptions **paraphrase** their requirements ("container orchestration"
  rather than "kubernetes"), so lexical methods can't win by string matching.
- Resume and JD wording use **disjoint vocabularies** — JDs never echo the
  resume's job title or phrasing.
- Relevance is **graded** (3 = same domain, 1 = related, 0 = unrelated).
- Resumes carry ~45% cross-domain skill noise.

Without those properties every lexical baseline saturates at nDCG 1.0 and the
harness tells you nothing.

---

## Using your own data

Create a directory with three files:

**`resumes.jsonl`**
```json
{"resume_id": "r001", "candidate_id": "c001", "category": "data_analyst", "text": "..."}
```

**`jobs.jsonl`**
```json
{"job_id": "j001", "category": "data_analyst", "title": "Data Analyst", "text": "..."}
```

**`qrels.csv`** — relevance judgements
```csv
job_id,resume_id,relevance
j001,r001,3
j001,r002,1
```

Relevance is graded 0–3. Unjudged pairs are treated as 0 (standard IR convention).

`candidate_id` matters: the split is grouped by it, so two resumes from the
same person can never straddle train and test.

---

## Labelling strategies, in ascending order of credibility

| Strategy | Effort | Credibility | How to describe it |
|---|---|---|---|
| **Proxy labels** — resume's own category vs job category | Minutes | Low | "Measures category alignment, not hiring fit" |
| **Human annotation** — N pairs rated 1–5 by 2+ people | Days | High | Report Cohen's κ for inter-annotator agreement |
| **Real outcomes** — was the candidate shortlisted? | Rarely obtainable | Highest | The gold standard |

Whichever you use, pass it via `--label-source` and it gets printed in the
report. If it contains "proxy" or "synthetic", the report auto-inserts a
warning banner — so you can't accidentally present weak labels as strong ones.

**Say the real number.** An honest "60 hand-labelled pairs, κ = 0.71" beats a
vague claim about a large dataset every time.

---

## What gets measured

**Systems** (in interpretive order):

1. `Random (floor)` — proves the task is non-trivial
2. `Jaccard keyword overlap` — what a naive ATS effectively does
3. `BM25` — strong classical lexical baseline
4. `TF-IDF cosine` — **the default baseline your model must beat**
5. `BERT whole-doc` — embeddings, no chunking
6. `BERT + section weighting` — **the ablation**: isolates the chunking contribution

**Metrics:** nDCG@{1,3,5,10}, P@k, Recall@k, MRR, MAP, plus Spearman for the
continuous quality score.

**Statistics:** bootstrap 95% CIs, and a **paired bootstrap** significance test
against the baseline. Pairing matters — both systems see the same queries, so
query difficulty is controlled for.

> With 20 evaluation queries, 0.79 vs 0.82 is probably noise. The harness tells
> you whether a gap is real instead of letting you claim it.

---

## Plugging in your real pipeline

Add a class to `harness/scorers.py`:

```python
class ResumeAnalyserScorer:
    name = "Resume Analyser (full)"

    def __init__(self):
        from app.scoring import score_resume_against_job
        self._score = score_resume_against_job

    def fit(self, corpus): pass

    def score(self, job_text, resume_texts):
        import numpy as np
        return np.array([
            self._score(rt, job_text)["job_fit_pct"] for rt in resume_texts
        ])
```

Then register it in `build_scorers()` in `run_eval.py`. It's now measured
identically to every baseline.

---

## Leakage guards (built in)

1. **Grouped splitting** by `candidate_id`, with an assertion that no candidate
   spans both sides. Splitting by row is the most common cause of inflated
   student-project numbers.
2. **Vectorisers fit on train only.** Fitting TF-IDF on all data before
   splitting leaks test vocabulary and IDF statistics — subtle and very common.
3. **Deterministic tie-breaking** on `(-score, resume_id)`, so ties don't
   resolve by array order and results reproduce across machines.
4. **Seeded everything.** Same seed + same data = identical metrics.

---

## Wiring into CI

```yaml
- name: Evaluation regression check
  run: |
    python run_eval.py --data data/eval --out results
    python -c "
    import csv, sys
    rows = {r['system']: float(r['nDCG@5']) for r in csv.DictReader(open('results/results.csv'))}
    threshold = 0.75
    actual = rows.get('Resume Analyser (full)', 0)
    if actual < threshold:
        sys.exit(f'Regression: nDCG@5 {actual:.3f} < {threshold}')
    "
```

This turns evaluation into a gate: a commit that degrades ranking quality
fails the build instead of shipping quietly.

---

## Honest limitations

- Proxy labels measure category alignment, not genuine hiring fit.
- 20 queries is a small evaluation set — the CIs are correspondingly wide.
- **No fairness evaluation yet.** Resume scoring encodes bias from names,
  universities, and employment gaps. A responsible next step is subgroup
  metrics: run the harness on name-swapped resumes and check whether scores
  shift. If they do, that's a finding worth reporting, not hiding.
