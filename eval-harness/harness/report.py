"""Report generation: markdown table, CSV, and a comparison chart."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .runner import SystemResult

NAVY, TEAL, GOLD, GREY = "#1F3A5F", "#2E8B8B", "#C9962C", "#8A93A0"


def write_csv(results: list[SystemResult], metrics: list[str], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["system"] + metrics + ["ms_per_query"])
        for r in results:
            w.writerow(
                [r.name] + [f"{r.mean(m):.4f}" for m in metrics]
                + [f"{r.latency_ms_per_query:.1f}"]
            )


def write_markdown(
    results: list[SystemResult],
    metrics: list[str],
    primary_metric: str,
    pvalues: dict[str, float],
    dataset_repr: str,
    label_source: str,
    path: Path,
    baseline_name: str,
) -> None:
    lines: list[str] = []
    a = lines.append

    a("# Resume Analyser — Evaluation Report\n")
    a(f"*Generated {datetime.now():%Y-%m-%d %H:%M}*\n")

    a("## Dataset\n")
    a(f"- `{dataset_repr}`")
    a(f"- **Label source:** {label_source}")
    a("- **Split:** grouped by `candidate_id` (no candidate appears in both splits)\n")

    if "proxy" in label_source.lower() or "synthetic" in label_source.lower():
        a("> ⚠️ **Labels are proxy labels, not human relevance judgements.** These "
          "numbers measure category alignment, not true hiring fit. State this "
          "limitation explicitly whenever you quote them.\n")

    a("## Results\n")
    header = "| System | " + " | ".join(metrics) + " | ms/query |"
    a(header)
    a("|" + "---|" * (len(metrics) + 2))
    for r in results:
        row = f"| {r.name} | " + " | ".join(f"{r.mean(m):.3f}" for m in metrics)
        row += f" | {r.latency_ms_per_query:.1f} |"
        a(row)
    a("")

    a(f"## {primary_metric} with 95% confidence intervals\n")
    a("| System | Mean | 95% CI | vs baseline |")
    a("|---|---|---|---|")
    for r in results:
        mean, lo, hi = r.ci(primary_metric)
        if r.name == baseline_name:
            verdict = "— (baseline)"
        else:
            p = pvalues.get(r.name, float("nan"))
            delta = mean - next(x.mean(primary_metric) for x in results
                                if x.name == baseline_name)
            sig = "significant" if p < 0.05 else "not significant"
            verdict = f"{delta:+.3f} (p={p:.3f}, {sig})"
        a(f"| {r.name} | {mean:.3f} | [{lo:.3f}, {hi:.3f}] | {verdict} |")
    a("")
    a("> Significance is a **paired bootstrap** over queries: the same queries are "
      "resampled for both systems, so query difficulty is controlled for. "
      "A gap that isn't significant should not be claimed as an improvement.\n")

    a("## How to read this\n")
    a("- **Random (floor)** proves the task is non-trivial. If a system scores near "
      "it, the metric or the labels are broken.")
    a("- **Jaccard / BM25 / TF-IDF** are the baselines your model must beat to be "
      "worth its complexity.")
    a("- The **section-weighting** row is an ablation: it isolates the contribution "
      "of the chunking strategy specifically.\n")

    path.write_text("\n".join(lines), encoding="utf-8")


def plot_comparison(
    results: list[SystemResult], metric: str, path: Path, baseline_name: str
) -> None:
    names = [r.name for r in results]
    means, los, his = [], [], []
    for r in results:
        m, lo, hi = r.ci(metric)
        means.append(m); los.append(m - lo); his.append(hi - m)

    colors = []
    for n in names:
        if "Random" in n:
            colors.append(GREY)
        elif n == baseline_name:
            colors.append(GOLD)
        elif "BERT" in n:
            colors.append(TEAL)
        else:
            colors.append(NAVY)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    y = range(len(names))
    ax.barh(list(y), means, xerr=[los, his], color=colors,
            edgecolor="white", capsize=4, height=0.62)

    # Label sits clear of THIS bar's error whisker, not a global offset
    for i, (m, h) in enumerate(zip(means, his)):
        ax.text(m + h + 0.022, i, f"{m:.3f}",
                va="center", fontsize=10, color="#222", fontweight="bold")

    ax.set_yticks(list(y))
    ax.set_yticklabels(names, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel(metric, fontsize=11)
    ax.set_title(f"{metric} by system (95% CI)", fontsize=13,
                 fontweight="bold", color=NAVY, pad=14)
    ax.set_xlim(0, max(m + h for m, h in zip(means, his)) + 0.14)
    ax.grid(axis="x", color="#E3E7EC", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#CBD2D9")

    plt.tight_layout()
    plt.savefig(path, dpi=170, facecolor="white")
    plt.close()
