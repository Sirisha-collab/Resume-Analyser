"""
Export evaluation results as JSON for the React dashboard.

The harness is an offline tool; React needs its output as data. This writes
a single `dashboard.json` that the frontend can either import statically or
fetch from the backend.

Two delivery paths:

  STATIC  copy dashboard.json into frontend/src/data/ and import it.
          No backend involved. Simplest, but you re-copy after each run.

  API     point the backend at your results directory and let React fetch
          /api/v1/eval/latest. Always current, needs the route wired up.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def export_json(results, metric, baseline_name, pvalues, dataset_repr,
                label_source, warnings, alert, out_path,
                diag=None, n_folds=0, all_metrics=None) -> Path:
    all_metrics = all_metrics or ["nDCG@5", "nDCG@10", "P@5", "Recall@10", "MRR", "MAP"]

    rand = next((r for r in results if "Random" in r.name), None)
    others = [r for r in results if r is not rand]
    best = max(others, key=lambda r: r.mean(metric)) if others else None

    rand_score = rand.mean(metric) if rand else 0.0
    best_score = best.mean(metric) if best else 0.0

    systems = []
    for r in results:
        mean, lo, hi = r.ci(metric)
        p = pvalues.get(r.name)
        systems.append({
            "name": r.name,
            "isRandom": "Random" in r.name,
            "isBaseline": r.name == baseline_name,
            "isBest": bool(best and r.name == best.name),
            "primary": round(mean, 4),
            "ciLow": round(lo, 4),
            "ciHigh": round(hi, 4),
            "pValue": None if p is None else round(p, 4),
            "significant": None if p is None else bool(p < 0.05),
            "latencyMs": round(r.latency_ms_per_query, 1),
            "metrics": {m: round(r.mean(m), 4) for m in all_metrics},
            "nObservations": len(r.per_query.get(metric, [])),
        })

    payload = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "dataset": dataset_repr,
        "labelSource": label_source,
        "primaryMetric": metric,
        "baselineName": baseline_name,
        "evaluationMode": f"{n_folds}-fold cross-validation" if n_folds > 1
                          else "single split",
        "nFolds": n_folds,
        "health": {
            "healthy": alert is None,
            "alert": alert,
            "warnings": list(warnings or []),
            "randomFloor": round(rand_score, 4),
            "bestScore": round(best_score, 4),
            "spread": round(best_score - rand_score, 4),
            # Surfaced so the UI can warn without re-deriving the rule
            "labelsAreAutomated": any(
                w in (label_source or "").lower()
                for w in ("proxy", "auto", "synthetic")
            ),
        },
        "allMetrics": all_metrics,
        "systems": systems,
        "diagnostics": None,
    }

    if diag:
        payload["diagnostics"] = {
            "scorer": diag["scorer"],
            "taxonomy": diag["taxonomy"],
            "worst": [
                {
                    "jobId": w["job_id"],
                    "title": w["title"],
                    "score": round(w["ndcg"], 4),
                    "nRelevant": w["n_relevant"],
                    "failure": w["failure"],
                }
                for w in diag["worst"]
            ],
            "perQuery": [
                {
                    "jobId": q["job_id"],
                    "title": q["title"],
                    "score": round(q["ndcg"], 4),
                    "nRelevant": q["n_relevant"],
                    "failure": q["failure"],
                }
                for q in diag["per_query"]
            ],
        }

    p = Path(out_path)
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return p
