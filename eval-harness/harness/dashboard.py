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

:root{
 --navy:%(navy)s; --navy-dk:%(navy_dk)s; --teal:%(teal)s; --gold:%(gold)s;
 --red:%(red)s; --grey:%(grey)s; --light:%(light)s; --green:%(green)s;
 --ink:#16202C; --bg:#F1F4F8; --line:#E2E8F0; --line-soft:#EDF1F6;
 --mono:ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace;
 --shadow:0 1px 2px rgba(20,39,63,.05),0 10px 26px -16px rgba(20,39,63,.35);
}

body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
 background:var(--bg);color:var(--ink);line-height:1.55;padding:0 0 56px;
 -webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
.wrap{max-width:1180px;margin:0 auto;padding:0 24px}

header{background:linear-gradient(135deg,var(--navy-dk),var(--navy) 60%%,#27507F);
 color:#fff;padding:34px 0 36px;margin-bottom:26px;position:relative;
 box-shadow:0 12px 30px -22px rgba(20,39,63,.9)}
header:after{content:"";position:absolute;left:0;right:0;bottom:0;height:3px;
 background:linear-gradient(90deg,var(--teal),var(--gold))}
header h1{font-size:27px;font-weight:700;letter-spacing:-.5px}
header .sub{color:#B3C7DA;font-size:13.5px;margin-top:6px;max-width:64ch}
header .meta{color:#89A2BC;font-size:11.5px;margin-top:10px;font-family:var(--mono);
 letter-spacing:.2px;word-break:break-word}
header .meta:first-of-type{margin-top:16px}

.banner{border-radius:12px;padding:16px 20px;margin-bottom:24px;display:flex;
 gap:14px;align-items:flex-start;box-shadow:var(--shadow)}
.banner.ok{background:linear-gradient(180deg,#F1FAF5,#E8F5EE);border:1px solid #A9D6BF}
.banner.bad{background:linear-gradient(180deg,#FEF2F0,#FDECEA);border:1px solid #F0B4AC}
.banner .icon{font-size:17px;line-height:1.35;width:28px;height:28px;flex:0 0 28px;
 border-radius:50%%;display:flex;align-items:center;justify-content:center;color:#fff}
.banner.ok .icon{background:var(--green)}
.banner.bad .icon{background:var(--red)}
.banner h3{font-size:15px;margin-bottom:3px;letter-spacing:-.2px}
.banner.ok h3{color:var(--green)}
.banner.bad h3{color:var(--red)}
.banner p{font-size:13.5px;color:#44505f}
.banner ul{margin:9px 0 0 18px;font-size:13px;color:#44505f}
.banner li{margin:3px 0}

.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(196px,1fr));
 gap:16px;margin-bottom:26px}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;
 padding:17px 18px 16px;position:relative;overflow:hidden;box-shadow:var(--shadow)}
.card:before{content:"";position:absolute;left:0;right:0;top:0;height:3px;
 background:var(--accent,var(--navy));opacity:.85}
.card .label{font-size:10.5px;text-transform:uppercase;letter-spacing:1px;
 color:var(--grey);font-weight:700}
.card .value{font-size:31px;font-weight:700;margin:7px 0 3px;letter-spacing:-.8px;
 line-height:1.1;font-family:var(--mono)}
.card .note{font-size:11.5px;color:var(--grey)}

section{background:#fff;border:1px solid var(--line);border-radius:14px;
 padding:22px 24px 24px;margin-bottom:22px;box-shadow:var(--shadow)}
section h2{font-size:16.5px;color:var(--navy);margin-bottom:4px;letter-spacing:-.25px;
 display:flex;align-items:center;gap:9px}
section h2:before{content:"";width:4px;height:15px;border-radius:2px;
 background:linear-gradient(180deg,var(--teal),var(--navy))}
section .hint{font-size:12.5px;color:var(--grey);margin-bottom:16px;max-width:82ch}

.tablewrap{border:1px solid var(--line-soft);border-radius:10px;overflow:hidden}
table{width:100%%;border-collapse:collapse;font-size:13px}
th{background:var(--navy);color:#fff;text-align:left;padding:10px 12px;font-weight:600;
 font-size:11.5px;letter-spacing:.35px;text-transform:uppercase;white-space:nowrap}
th.num{text-align:right}
td{padding:10px 12px;border-bottom:1px solid var(--line-soft);vertical-align:middle}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover td{background:#F7F9FC}
tr.dim td{color:var(--grey);background:#FAFBFC}
tr.dim:hover td{background:#F5F7FA}
tr.best td{background:#FFFBF0;font-weight:600}
tr.best:hover td{background:#FFF7E4}
tr.best td:first-child{box-shadow:inset 3px 0 0 var(--gold)}
.num{font-family:var(--mono);text-align:right;white-space:nowrap}

.bar{position:relative;background:var(--line-soft);border-radius:4px;height:20px;
 min-width:110px;display:inline-block;vertical-align:middle;width:132px;
 overflow:hidden;box-shadow:inset 0 0 0 1px rgba(20,39,63,.05)}
.bar span{position:absolute;left:0;top:0;bottom:0;border-radius:4px}
.barval{display:inline-block;vertical-align:middle;margin-left:10px;font-size:12px;
 font-family:var(--mono);color:var(--ink);font-weight:600}

.chart{margin-top:4px}
.chart svg{display:block;width:100%%;height:auto}

.ci{font-family:var(--mono);font-size:12px;color:var(--grey);white-space:nowrap}
.tag{display:inline-block;padding:2.5px 9px;border-radius:999px;font-size:11px;
 font-weight:600;font-family:var(--mono);white-space:nowrap;border:1px solid transparent}
.tag.sig{background:#E8F5EE;color:var(--green);border-color:#BCE0CD}
.tag.ns{background:#FDF3E3;color:#8A6D1F;border-color:#EBD7AC}
.tag.base{background:var(--light);color:var(--grey);border-color:#DCE4EC}

.fail{display:grid;grid-template-columns:minmax(230px,280px) 1fr;gap:26px;
 align-items:start}
.frow{display:flex;align-items:center;gap:9px;margin-bottom:8px;font-size:12.5px}
.frow .nm{width:104px;color:var(--grey);font-weight:600;letter-spacing:.1px}
.frow .n{width:26px;text-align:right;font-family:var(--mono);font-weight:700}
.frow .fbar{flex:1;height:16px;background:var(--line-soft);border-radius:4px;
 overflow:hidden;box-shadow:inset 0 0 0 1px rgba(20,39,63,.05)}
.frow .fbar i{display:block;height:100%%;border-radius:4px}
.frow .pct{width:40px;text-align:right;font-family:var(--mono);font-size:11px;
 color:var(--grey)}

.footer{font-size:11.5px;color:var(--grey);text-align:center;margin-top:10px;
 line-height:1.7}
.caveat{background:linear-gradient(90deg,#FFF8EC,#FFFDF8);border:1px solid #F0E2C4;
 border-left:3px solid var(--gold);padding:11px 15px;border-radius:0 8px 8px 0;
 font-size:12.5px;color:#5A4600;margin-top:14px}
.caveat code{font-family:var(--mono);background:#FBEFD6;padding:1px 5px;
 border-radius:4px;font-size:11.5px}

@media (max-width:820px){
 .fail{grid-template-columns:1fr;gap:20px}
 .tablewrap{overflow-x:auto}
 header h1{font-size:22px}
 .card .value{font-size:27px}
}

@media print{
 body{background:#fff;padding:0}
 header{box-shadow:none;margin-bottom:18px}
 section,.card,.banner{box-shadow:none;break-inside:avoid}
 *{-webkit-print-color-adjust:exact;print-color-adjust:exact}
}
""" % {"navy": NAVY, "navy_dk": NAVY_DK, "teal": TEAL, "gold": GOLD, "red": RED,
       "grey": GREY, "light": LIGHT, "green": GREEN}


def _bar(value: float, vmax: float, color: str) -> str:
    pct = 0 if vmax <= 0 else max(2.0, min(100.0, value / vmax * 100))
    return (f'<div class="bar"><span style="width:{pct:.1f}%;'
            f'background:linear-gradient(90deg,{color}C0,{color})"></span>'
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
    rows = [(r.name, *r.ci(metric)) for r in results]
    if not rows:
        return ""
    vmax = max(hi for _, _, _, hi in rows)
    vmax = min(1.0, vmax * 1.15) if vmax > 0 else 1.0
    # best = strongest real system; the Random floor is never "best"
    ranked = [x for x in rows if "Random" not in x[0]] or rows
    best = max(ranked, key=lambda x: x[1])[0]

    W, LEFT, RIGHT = 1060, 240, 74
    row_h, top = 42, 40
    H = top + row_h * len(rows) + 34
    plot = W - LEFT - RIGHT

    def x(v):
        return LEFT + (max(0.0, min(v, vmax)) / vmax) * plot

    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" '
           f'preserveAspectRatio="xMidYMid meet" '
           f'xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">']

    # alternating row bands
    for i in range(len(rows)):
        if i % 2:
            y0 = top + row_h * i
            out.append(f'<rect x="{LEFT}" y="{y0}" width="{plot}" height="{row_h}" '
                       f'fill="#F7F9FC"/>')

    # gridlines
    ticks = [i / 5 * vmax for i in range(6)]
    for t in ticks:
        out.append(f'<line x1="{x(t):.1f}" y1="{top-16}" x2="{x(t):.1f}" y2="{H-30}" '
                   f'stroke="#E3E7EC" stroke-width="1"/>')
        out.append(f'<text x="{x(t):.1f}" y="{H-12}" font-size="11" fill="{GREY}" '
                   f'text-anchor="middle" font-family="ui-monospace,monospace">'
                   f'{t:.2f}</text>')
    # axis baseline + label
    out.append(f'<line x1="{LEFT}" y1="{H-30}" x2="{LEFT+plot}" y2="{H-30}" '
               f'stroke="#CBD4DE" stroke-width="1"/>')
    out.append(f'<text x="{LEFT-14}" y="{top-16}" font-size="10.5" fill="{GREY}" '
               f'text-anchor="end" letter-spacing="1">{html.escape(metric.upper())}</text>')

    for i, (name, mean, lo, hi) in enumerate(rows):
        y = top + row_h * i + row_h / 2
        c = _color_for(name, name == best)
        weight = "700" if name == best else "400"
        out.append(f'<text x="{LEFT-14}" y="{y+4}" font-size="12.5" fill="#16202C" '
                   f'font-weight="{weight}" text-anchor="end">'
                   f'{html.escape(name)}</text>')
        out.append(f'<rect x="{LEFT}" y="{y-11}" width="{max(1,x(mean)-LEFT):.1f}" '
                   f'height="22" fill="{c}" rx="4" opacity=".92"/>')
        # whiskers
        out.append(f'<line x1="{x(lo):.1f}" y1="{y}" x2="{x(hi):.1f}" y2="{y}" '
                   f'stroke="#33404F" stroke-width="1.6"/>')
        for xv in (lo, hi):
            out.append(f'<line x1="{x(xv):.1f}" y1="{y-7}" x2="{x(xv):.1f}" y2="{y+7}" '
                       f'stroke="#33404F" stroke-width="1.6" stroke-linecap="round"/>')
        out.append(f'<text x="{x(hi)+10:.1f}" y="{y+4}" font-size="12" font-weight="600" '
                   f'fill="#16202C" font-family="ui-monospace,monospace">'
                   f'{mean:.3f}</text>')
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
    def card(label, value, note, color="#16202C"):
        return (f'<div class="card" style="--accent:{color}">'
                f'<div class="label">{label}</div>'
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
             f"metric: {html.escape(str(metric))}", TEAL),
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
            f'<td style="width:270px">{_bar(r.mean(metric), vmax, _color_for(r.name, is_best))}</td>'
            f'<td class="ci">[{lo:.3f}, {hi:.3f}]</td>'
            f'<td>{tag}</td>'
            f'<td class="num">{r.mean("MRR"):.3f}</td>'
            f'<td class="num">{r.mean("MAP"):.3f}</td>'
            f'<td class="num">{r.latency_ms_per_query:.1f}</td></tr>'
        )
    table = ('<div class="tablewrap"><table><thead><tr><th>System</th><th>' +
             html.escape(str(metric)) +
             "</th><th>95% CI</th><th>vs baseline</th><th class='num'>MRR</th>"
             "<th class='num'>MAP</th><th class='num'>ms/query</th></tr></thead>"
             "<tbody>" + "".join(trs) + "</tbody></table></div>")

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
                f'<div class="frow"><span class="nm">{html.escape(k)}</span>'
                f'<span class="n">{n}</span>'
                f'<span class="fbar"><i style="width:{n/total*100:.0f}%;'
                f'background:{FAIL_COLORS.get(k, GREY)}"></i></span>'
                f'<span class="pct">{n/total*100:.0f}%</span></div>')
        worst = "".join(
            f'<tr><td class="num">{w["ndcg"]:.3f}</td><td class="num">{w["n_relevant"]}</td>'
            f'<td><span class="tag" style="background:'
            f'{FAIL_COLORS.get(w["failure"], GREY)}1A;'
            f'border-color:{FAIL_COLORS.get(w["failure"], GREY)}40;'
            f'color:{FAIL_COLORS.get(w["failure"], GREY)}">'
            f'{html.escape(str(w["failure"]))}</span></td>'
            f'<td>{html.escape(w["title"])}</td></tr>'
            for w in diag["worst"])
        hints = "".join(
            f'<div class="caveat"><b>{k}</b> &mdash; {FAIL_HINT[k]}</div>'
            for k in ("no_relevant", "distractor_top", "buried") if tax.get(k))
        fail_html = f"""
<section><h2>Failure analysis &mdash; {html.escape(diag['scorer'])}</h2>
<p class="hint">Which queries failed, and what kind of fix each needs.</p>
<div class="fail"><div>{''.join(bars)}</div>
<div class="tablewrap"><table><thead><tr><th class="num">{html.escape(str(metric))}</th>
<th class="num">#rel</th><th>Failure</th>
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
<section><h2>{html.escape(str(metric))} with 95% confidence intervals</h2>
<p class="hint">Whiskers show the bootstrap interval. Overlapping intervals mean
the difference is not established.</p>
<div class="chart">{_ci_svg(results, metric, baseline_name)}</div></section>
{fail_html}
<div class="footer">Generated by the Resume Analyser evaluation harness &middot;
significance via paired bootstrap over queries</div>
</div></body></html>"""

    p = Path(out_path)
    p.write_text(doc, encoding="utf-8")
    return p
