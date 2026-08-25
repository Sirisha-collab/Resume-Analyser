"""
Self-contained HTML dashboard.

Produces one .html file with no external dependencies — no CDN, no network.
Opens in any browser, works offline, and screenshots cleanly for a report.

    from harness.dashboard import render_dashboard
    render_dashboard(results, ..., out_path)
"""
from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

NAVY = "#1F3A5F"
NAVY_DK = "#14273F"
TEAL = "#2E8B8B"
GOLD = "#C9962C"
RED = "#B03A2E"
GREY = "#5A6472"
LIGHT = "#EEF2F6"
GREEN = "#2E7D5B"

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
 background:#F4F6F8;color:#1f2937;line-height:1.5;padding:0 0 48px}
.wrap{max-width:1180px;margin:0 auto;padding:0 24px}
header{background:%(navy)s;color:#fff;padding:28px 0 30px;margin-bottom:26px}
header h1{font-size:26px;font-weight:700;letter-spacing:-.4px}
header .sub{color:#A9BDD1;font-size:13.5px;margin-top:5px}
header .meta{color:#8CA3BB;font-size:12px;margin-top:12px;font-family:ui-monospace,monospace}

.banner{border-radius:10px;padding:16px 20px;margin-bottom:24px;display:flex;
 gap:14px;align-items:flex-start}
.banner.ok{background:#E8F5EE;border:1px solid #A9D6BF}
.banner.bad{background:#FDECEA;border:1px solid #F0B4AC}
.banner .icon{font-size:20px;line-height:1.2}
.banner h3{font-size:15px;margin-bottom:3px}
.banner.ok h3{color:%(green)s}.banner.bad h3{color:%(red)s}
.banner p{font-size:13.5px;color:#44505f}
.banner ul{margin:8px 0 0 18px;font-size:13px;color:#44505f}
.banner li{margin:3px 0}

.cards{display:flex;flex-wrap:wrap;gap:16px;margin-bottom:26px}
.card{background:#fff;border:1px solid #E1E6EC;border-radius:10px;padding:16px 18px;
 flex:1 1 0;min-width:190px}
.card .label{font-size:11px;text-transform:uppercase;letter-spacing:.9px;color:%(grey)s;
 font-weight:600}
.card .value{font-size:29px;font-weight:700;margin:6px 0 2px;letter-spacing:-.5px}
.card .note{font-size:11.5px;color:%(grey)s}

section{background:#fff;border:1px solid #E1E6EC;border-radius:10px;
 padding:22px 24px;margin-bottom:22px}
section h2{font-size:16px;color:%(navy)s;margin-bottom:4px}
section .hint{font-size:12.5px;color:%(grey)s;margin-bottom:16px}

table{width:100%%;border-collapse:collapse;font-size:13px}
th{background:%(navy)s;color:#fff;text-align:left;padding:9px 11px;font-weight:600;
 font-size:12px}
th:first-child{border-radius:6px 0 0 0}th:last-child{border-radius:0 6px 0 0}
td{padding:9px 11px;border-bottom:1px solid #EDF0F4}
tr:last-child td{border-bottom:none}
tr.dim td{color:%(grey)s;background:#FAFBFC}
tr.best td{background:#FFF9EC;font-weight:600}
.num{font-family:ui-monospace,monospace;text-align:right}

.bar{position:relative;background:#EDF0F4;border-radius:3px;height:19px;min-width:110px;
 display:inline-block;vertical-align:middle;width:132px}
.bar span{position:absolute;left:0;top:0;bottom:0;border-radius:3px}
.barval{display:inline-block;vertical-align:middle;margin-left:9px;font-size:12px;
 font-family:ui-monospace,monospace;color:#1f2937;font-weight:600}

.fail{display:flex;flex-wrap:wrap;gap:26px;align-items:flex-start}
.fail>div:first-child{flex:0 0 230px}
.fail>div:last-child{flex:1 1 380px}

.ci{font-family:ui-monospace,monospace;font-size:12px;color:%(grey)s}
.tag{display:inline-block;padding:2px 8px;border-radius:11px;font-size:11px;font-weight:600}
.tag.sig{background:#E8F5EE;color:%(green)s}
.tag.ns{background:#FDF3E3;color:#8A6D1F}
.tag.base{background:%(light)s;color:%(grey)s}

.fail{display:grid;grid-template-columns:220px 1fr;gap:26px;align-items:start}
.frow{display:flex;align-items:center;gap:9px;margin-bottom:7px;font-size:12.5px}
.frow .n{width:26px;text-align:right;font-family:ui-monospace,monospace;font-weight:600}
.frow .fbar{flex:1;height:15px;background:#EDF0F4;border-radius:3px;overflow:hidden}
.frow .fbar i{display:block;height:100%%}
.frow .nm{width:104px;color:%(grey)s}

.footer{font-size:11.5px;color:%(grey)s;text-align:center;margin-top:8px}
.caveat{background:#FFF8EC;border-left:3px solid %(gold)s;padding:11px 15px;
 border-radius:0 6px 6px 0;font-size:12.5px;color:#5A4600;margin-top:14px}

""" % {"navy": NAVY, "teal": TEAL, "gold": GOLD, "red": RED, "grey": GREY,
       "light": LIGHT, "green": GREEN}


def _bar(value: float, vmax: float, color: str) -> str:
    pct = 0 if vmax <= 0 else max(2.0, min(100.0, value / vmax * 100))
    return (f'<div class="bar"><span style="width:{pct:.1f}%;background:{color}"></span>'
            f'</div><span class="barval">{value:.3f}</span>')


def _color_for(name: str, is_best: bool) -> str:
    if "Random" in name:
        return "#B8C2CC"
    if is_best:
        return GOLD
    if "BERT" in name:
        return TEAL
    return NAVY


def _ci_svg(results, metric: str, baseline_name: str) -> str:
    """Confidence-interval chart as inline SVG — no JS, no CDN."""
    rows = [(r.name, *r.ci(metric)) for r in results]
    if not rows:
        return ""
    vmax = max(hi for _, _, _, hi in rows)
    vmax = min(1.0, vmax * 1.15) if vmax > 0 else 1.0
    best = max(rows, key=lambda x: x[1])[0]

    W, LEFT, RIGHT = 1060, 230, 60
    row_h, top = 40, 34
    H = top + row_h * len(rows) + 26
    plot = W - LEFT - RIGHT

    def x(v):
        return LEFT + (v / vmax) * plot

    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" '
           f'xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">']
    # gridlines
    ticks = [i / 5 * vmax for i in range(6)]
    for t in ticks:
        out.append(f'<line x1="{x(t):.1f}" y1="{top-12}" x2="{x(t):.1f}" y2="{H-24}" '
                   f'stroke="#E3E7EC" stroke-width="1"/>')
        out.append(f'<text x="{x(t):.1f}" y="{H-8}" font-size="11" fill="{GREY}" '
                   f'text-anchor="middle">{t:.2f}</text>')

    for i, (name, mean, lo, hi) in enumerate(rows):
        y = top + row_h * i + row_h / 2
        c = _color_for(name, name == best)
        out.append(f'<text x="{LEFT-14}" y="{y+4}" font-size="12.5" fill="#1f2937" '
                   f'text-anchor="end">{html.escape(name)}</text>')
        out.append(f'<rect x="{LEFT}" y="{y-10}" width="{max(1,x(mean)-LEFT):.1f}" '
                   f'height="20" fill="{c}" rx="3"/>')
        # whiskers
        out.append(f'<line x1="{x(lo):.1f}" y1="{y}" x2="{x(hi):.1f}" y2="{y}" '
                   f'stroke="#33404F" stroke-width="1.6"/>')
        for xv in (lo, hi):
            out.append(f'<line x1="{x(xv):.1f}" y1="{y-6}" x2="{x(xv):.1f}" y2="{y+6}" '
                       f'stroke="#33404F" stroke-width="1.6"/>')
        out.append(f'<text x="{x(hi)+9:.1f}" y="{y+4}" font-size="12" font-weight="600" '
                   f'fill="#1f2937">{mean:.3f}</text>')
    out.append("</svg>")
    return "".join(out)


FAIL_COLORS = {"ok": GREEN, "partial": TEAL, "buried": GOLD,
               "distractor_top": "#D97706", "no_relevant": RED}

FAIL_HINT = {
    "no_relevant": "Label problem — no relevant resume exists for this query.",
    "distractor_top": "An irrelevant resume ranked #1 — check shared generic wording.",
    "buried": "Relevant resumes exist but rank below k — recall failure.",
    "partial": "Right documents, imperfect ordering. Usually acceptable.",
    "ok": "Strong result.",
}


def render_dashboard(results, metric, baseline_name, pvalues, dataset_repr,
                     label_source, warnings, alert, out_path,
                     diag=None, n_folds=0) -> Path:
    ts = datetime.now().strftime("%d %b %Y, %H:%M")
    rand = next((r for r in results if "Random" in r.name), None)
    others = [r for r in results if r is not rand]
    best = max(others, key=lambda r: r.mean(metric)) if others else None

    rand_score = rand.mean(metric) if rand else 0.0
    best_score = best.mean(metric) if best else 0.0
    spread = best_score - rand_score
    healthy = alert is None

    # ---------- banner ----------
    if healthy:
        banner = (f'<div class="banner ok"><div class="icon">&#10003;</div><div>'
                  f'<h3>Evaluation looks healthy</h3>'
                  f'<p>Random floor is {rand_score:.3f} and the usable spread is '
                  f'{spread:.3f}. These numbers are safe to read.</p></div></div>')
    else:
        items = "".join(f"<li>{html.escape(w)}</li>" for w in (warnings or []))
        banner = (f'<div class="banner bad"><div class="icon">&#9888;</div><div>'
                  f'<h3>Results are not usable</h3><p>{html.escape(alert)}</p>'
                  + (f"<ul>{items}</ul>" if items else "") +
                  '</div></div>')

    # ---------- KPI cards ----------
    def card(label, value, note, color="#1f2937"):
        return (f'<div class="card"><div class="label">{label}</div>'
                f'<div class="value" style="color:{color}">{value}</div>'
                f'<div class="note">{note}</div></div>')

    rand_c = GREEN if rand_score < 0.4 else RED
    spread_c = GREEN if spread > 0.35 else RED
    cards = "".join([
        card("Random floor", f"{rand_score:.3f}",
             "healthy &lt; 0.40" if rand_score < 0.4 else "too high — fix labels", rand_c),
        card("Best system", f"{best_score:.3f}",
             html.escape(best.name) if best else "&mdash;", NAVY),
        card("Usable spread", f"{spread:.3f}",
             "good separation" if spread > 0.35 else "too compressed", spread_c),
        card("Evaluation", f"{n_folds}-fold" if n_folds > 1 else "single split",
             f"metric: {metric}", TEAL),
    ])

    # ---------- results table ----------
    vmax = max(r.mean(metric) for r in results) if results else 1.0
    trs = []
    for r in results:
        is_rand = "Random" in r.name
        is_best = best is not None and r.name == best.name
        cls = "dim" if is_rand else ("best" if is_best else "")
        mean, lo, hi = r.ci(metric)
        if r.name == baseline_name:
            tag = '<span class="tag base">baseline</span>'
        elif is_rand:
            tag = '<span class="tag base">floor</span>'
        else:
            p = pvalues.get(r.name)
            if p is None:
                tag = ""
            elif p < 0.05:
                tag = f'<span class="tag sig">p={p:.3f}</span>'
            else:
                tag = f'<span class="tag ns">p={p:.3f} n.s.</span>'
        trs.append(
            f'<tr class="{cls}"><td>{html.escape(r.name)}</td>'
            f'<td style="width:210px">{_bar(r.mean(metric), vmax, _color_for(r.name, is_best))}</td>'
            f'<td class="ci">[{lo:.3f}, {hi:.3f}]</td>'
            f'<td>{tag}</td>'
            f'<td class="num">{r.mean("MRR"):.3f}</td>'
            f'<td class="num">{r.mean("MAP"):.3f}</td>'
            f'<td class="num">{r.latency_ms_per_query:.1f}</td></tr>'
        )
    table = ("<table><thead><tr><th>System</th><th>" + metric +
             "</th><th>95% CI</th><th>vs baseline</th><th>MRR</th><th>MAP</th>"
             "<th>ms/query</th></tr></thead><tbody>" + "".join(trs) + "</tbody></table>")

    # ---------- failure analysis ----------
    fail_html = ""
    if diag:
        tax = diag["taxonomy"]
        total = sum(tax.values()) or 1
        bars = []
        for k in ("ok", "partial", "buried", "distractor_top", "no_relevant"):
            n = tax.get(k, 0)
            if not n:
                continue
            bars.append(
                f'<div class="frow"><span class="nm">{k}</span>'
                f'<span class="n">{n}</span>'
                f'<span class="fbar"><i style="width:{n/total*100:.0f}%;'
                f'background:{FAIL_COLORS[k]}"></i></span></div>')
        worst = "".join(
            f'<tr><td class="num">{w["ndcg"]:.3f}</td><td class="num">{w["n_relevant"]}</td>'
            f'<td><span class="tag" style="background:{FAIL_COLORS[w["failure"]]}22;'
            f'color:{FAIL_COLORS[w["failure"]]}">{w["failure"]}</span></td>'
            f'<td>{html.escape(w["title"])}</td></tr>'
            for w in diag["worst"])
        hints = "".join(
            f'<div class="caveat"><b>{k}</b> &mdash; {FAIL_HINT[k]}</div>'
            for k in ("no_relevant", "distractor_top", "buried") if tax.get(k))
        fail_html = f"""
<section><h2>Failure analysis &mdash; {html.escape(diag['scorer'])}</h2>
<p class="hint">Which queries failed, and what kind of fix each needs.</p>
<div class="fail"><div>{''.join(bars)}</div>
<div><table><thead><tr><th>{metric}</th><th>#rel</th><th>Failure</th>
<th>Query</th></tr></thead><tbody>{worst}</tbody></table></div></div>
{hints}</section>"""

    proxy_note = ""
    if any(w in label_source.lower() for w in ("proxy", "auto", "synthetic")):
        proxy_note = (f'<div class="caveat"><b>Label caveat</b> &mdash; labels are '
                      f'<code>{html.escape(label_source)}</code>. These measure '
                      f'alignment with an automated rule, not verified human '
                      f'judgement. Validate against a hand-labelled sample before '
                      f'quoting these numbers.</div>')

    doc = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Resume Analyser &mdash; Evaluation Dashboard</title><style>{CSS}</style></head>
<body>
<header><div class="wrap"><h1>Resume Analyser &mdash; Evaluation Dashboard</h1>
<div class="sub">Ranking quality against baselines, with confidence intervals
and significance testing</div>
<div class="meta">{html.escape(dataset_repr)}</div>
<div class="meta">labels: {html.escape(label_source)} &nbsp;|&nbsp; generated {ts}</div>
</div></header>
<div class="wrap">
{banner}
<div class="cards">{cards}</div>
<section><h2>System comparison</h2>
<p class="hint">Every system ranks the same resumes for the same queries.
Random is the floor &mdash; if a system scores near it, the evaluation is broken,
not the model.</p>{table}{proxy_note}</section>
<section><h2>{metric} with 95% confidence intervals</h2>
<p class="hint">Whiskers show the bootstrap interval. Overlapping intervals mean
the difference is not established.</p>{_ci_svg(results, metric, baseline_name)}</section>
{fail_html}
<div class="footer">Generated by the Resume Analyser evaluation harness &middot;
significance via paired bootstrap over queries</div>
</div></body></html>"""

    p = Path(out_path)
    p.write_text(doc, encoding="utf-8")
    return p
