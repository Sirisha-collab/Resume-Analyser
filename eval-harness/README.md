# Evaluation Harness

A reproducible harness for measuring how well Resume Analyser ranks resumes
against job descriptions, with baselines, ablations, and statistical
significance testing.

This exists to answer two interview questions properly:
**"What dataset did you evaluate on and how?"** and **"What metrics and baseline?"**

---

## Quick start

```bash
pip install numpy pandas scikit-learn scipy matplotlib pytest
pip install sentence-transformers          # optional: enables the BERT scorers

python -m ingest.build_dataset --resumes "D:\Docs Latest\A Masters Required doc\Projects\Resume Analyser\ResumeAnalysis_PY\Samples\Resumes" --jobs "D:\Docs Latest\A Masters Required doc\Projects\Resume Analyser\ResumeAnalysis_PY\Samples\Job Description" --out data/real
<!-- Previous commands:
python -m ingest.make_qrels --data data\real --mode worksheet
python run_eval.py --data data\real --out results_real --label-source "hand-labelled, n=12" -->

New: 
python -m ingest.auto_label --data data\real --target-density 0.22

python run_eval.py --data data\real --out results_real --test-size 0.5 --label-source "hybrid auto (TECH_SKILLS + IDF)"
```
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
