# Resume Analyser — Evaluation Report

*Generated 2026-08-23 18:53*

## Dataset

- `Dataset(resumes=12, jobs=7, judgements=15, labels='hybrid auto (TECH_SKILLS + IDF)')`
- **Label source:** hybrid auto (TECH_SKILLS + IDF)
- **Split:** grouped by `candidate_id` (no candidate appears in both splits)

## Results

| System | nDCG@5 | nDCG@10 | P@5 | Recall@10 | MRR | MAP | ms/query |
|---|---|---|---|---|---|---|---|
| Random (floor) | 0.188 | 0.323 | 0.200 | 0.655 | 0.232 | 0.242 | 0.0 |
| Jaccard keyword overlap | 0.278 | 0.406 | 0.257 | 0.714 | 0.363 | 0.329 | 1.4 |
| BM25 | 0.439 | 0.532 | 0.257 | 0.714 | 0.548 | 0.473 | 1.1 |
| TF-IDF cosine | 0.471 | 0.509 | 0.343 | 0.714 | 0.476 | 0.456 | 4.4 |
| BERT whole-doc | 0.336 | 0.437 | 0.229 | 0.714 | 0.381 | 0.341 | 777.1 |
| BERT + section weighting | 0.377 | 0.445 | 0.257 | 0.655 | 0.393 | 0.362 | 1909.5 |

## nDCG@5 with 95% confidence intervals

| System | Mean | 95% CI | vs baseline |
|---|---|---|---|
| Random (floor) | 0.188 | [0.042, 0.332] | -0.283 (p=0.009, significant) |
| Jaccard keyword overlap | 0.278 | [0.058, 0.549] | -0.193 (p=0.207, not significant) |
| BM25 | 0.439 | [0.165, 0.715] | -0.032 (p=0.609, not significant) |
| TF-IDF cosine | 0.471 | [0.200, 0.722] | — (baseline) |
| BERT whole-doc | 0.336 | [0.142, 0.507] | -0.135 (p=0.110, not significant) |
| BERT + section weighting | 0.377 | [0.159, 0.571] | -0.094 (p=0.181, not significant) |

> Significance is a **paired bootstrap** over queries: the same queries are resampled for both systems, so query difficulty is controlled for. A gap that isn't significant should not be claimed as an improvement.

## How to read this

- **Random (floor)** proves the task is non-trivial. If a system scores near it, the metric or the labels are broken.
- **Jaccard / BM25 / TF-IDF** are the baselines your model must beat to be worth its complexity.
- The **section-weighting** row is an ablation: it isolates the contribution of the chunking strategy specifically.
