"""
Generate a synthetic sample dataset so the harness runs out of the box.

THIS IS NOT A REAL EVALUATION SET. It exists so you can verify the plumbing
works before wiring in real data. Numbers produced from it are meaningless
as evidence about your model — replace it with real resumes and, ideally,
human relevance judgements.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

# NOTE ON REALISM: resume wording and JD wording are deliberately kept
# DISJOINT (separate verb/object vocabularies, and JDs never echo the resume's
# job title). If both sides share phrasing, string matching solves the task and
# every lexical baseline saturates at nDCG 1.0 — which tells you nothing about
# your model. Real resumes and real JDs rarely use identical language, and that
# gap is exactly what semantic matching is supposed to close.
CATEGORIES = {
    "data_analyst": {
        "titles": ["Data Analyst", "Business Intelligence Analyst"],
        "skills": ["sql", "python", "power bi", "excel", "tableau", "statistics", "dbt"],
        "verbs": ["Built dashboards tracking", "Analysed trends in", "Automated reporting for"],
        "objects": ["revenue KPIs", "customer churn", "supply chain metrics", "campaign performance"],
        "jd_needs": ["turn raw operational data into decisions leadership can act on",
                     "own recurring performance reporting across the business",
                     "investigate anomalies in commercial metrics"],
    },
    "backend_engineer": {
        "titles": ["Backend Engineer", "Software Engineer (Backend)"],
        "skills": ["python", "java", "postgresql", "docker", "kubernetes", "redis", "fastapi", "kafka"],
        "verbs": ["Designed APIs for", "Scaled services handling", "Migrated infrastructure for"],
        "objects": ["payment processing", "user authentication", "order fulfilment", "event streaming"],
        "jd_needs": ["keep high-throughput services reliable under load",
                     "evolve our service boundaries as traffic grows",
                     "own reliability and latency for critical request paths"],
    },
    "ml_engineer": {
        "titles": ["Machine Learning Engineer", "ML Engineer"],
        "skills": ["python", "pytorch", "tensorflow", "scikit-learn", "nlp", "spark", "airflow", "mlflow"],
        "verbs": ["Trained models predicting", "Deployed pipelines for", "Improved accuracy of"],
        "objects": ["customer lifetime value", "document classification", "demand forecasting", "recommendation ranking"],
        "jd_needs": ["take predictive systems from prototype to production",
                     "improve the quality of automated decisioning",
                     "own retraining and monitoring of live models"],
    },
    "frontend_engineer": {
        "titles": ["Frontend Engineer", "UI Engineer"],
        "skills": ["javascript", "typescript", "react", "vue", "css", "figma", "webpack", "jest"],
        "verbs": ["Rebuilt interfaces for", "Optimised load times on", "Implemented design systems for"],
        "objects": ["the checkout flow", "the admin console", "a marketing site", "an analytics dashboard"],
        "jd_needs": ["deliver polished, accessible user experiences",
                     "raise the quality bar on our customer-facing surfaces",
                     "own perceived performance and interaction design in the client"],
    },
    "marketing": {
        "titles": ["Digital Marketing Specialist", "Growth Marketer"],
        "skills": ["seo", "sem", "analytics", "hubspot", "copywriting", "salesforce", "excel"],
        "verbs": ["Ran campaigns increasing", "Optimised funnels for", "Managed budgets driving"],
        "objects": ["organic traffic", "lead conversion", "brand awareness", "email engagement"],
        "jd_needs": ["grow qualified demand across acquisition channels",
                     "own the top of our commercial funnel",
                     "improve return on paid and organic spend"],
    },
}

UNIVERSITIES = ["State University", "Institute of Technology", "City College", "National University"]
DEGREES = ["B.Tech Computer Science", "B.Sc Statistics", "M.Sc Data Science", "BBA Marketing"]

# Job descriptions describe requirements in DIFFERENT WORDS than resumes use.
# This is the whole argument for semantic matching: a JD asking for "container
# orchestration" should match a resume saying "kubernetes". Without paraphrase,
# the synthetic data is trivially solvable by string matching and every lexical
# baseline saturates at 1.0, leaving no headroom to measure your model.
PARAPHRASE = {
    "sql": "relational query languages",
    "python": "scripting in a high-level language",
    "power bi": "business intelligence tooling",
    "tableau": "data visualisation platforms",
    "excel": "spreadsheet modelling",
    "statistics": "quantitative analysis",
    "dbt": "analytics transformation frameworks",
    "java": "statically typed JVM languages",
    "postgresql": "relational database systems",
    "docker": "containerisation",
    "kubernetes": "container orchestration",
    "redis": "in-memory caching layers",
    "fastapi": "modern async web frameworks",
    "kafka": "distributed event streaming",
    "pytorch": "deep learning frameworks",
    "tensorflow": "neural network libraries",
    "scikit-learn": "classical machine learning toolkits",
    "nlp": "natural language processing",
    "spark": "distributed data processing",
    "airflow": "workflow orchestration",
    "mlflow": "experiment tracking",
    "javascript": "browser scripting",
    "typescript": "typed frontend languages",
    "react": "component-based UI libraries",
    "vue": "reactive frontend frameworks",
    "css": "styling and layout",
    "figma": "design collaboration tools",
    "webpack": "module bundling",
    "jest": "frontend testing frameworks",
    "seo": "organic search optimisation",
    "sem": "paid search campaigns",
    "analytics": "web analytics platforms",
    "hubspot": "marketing automation suites",
    "copywriting": "persuasive content creation",
    "salesforce": "CRM platforms",
}

# Partially-overlapping domains earn GRADED relevance rather than 0.
# Real relevance is not binary — an ML engineer is a partial fit for a
# backend role, and a metric that ignores this overstates your system.
RELATED = {
    ("ml_engineer", "data_analyst"): 1,
    ("data_analyst", "ml_engineer"): 1,
    ("ml_engineer", "backend_engineer"): 1,
    ("backend_engineer", "ml_engineer"): 1,
    ("frontend_engineer", "backend_engineer"): 1,
    ("backend_engineer", "frontend_engineer"): 1,
}


def _resume_text(rng: random.Random, cat: str, noise: float) -> str:
    spec = CATEGORIES[cat]
    own = spec["skills"]
    n_own = max(2, int(len(own) * (1 - noise)))
    skills = rng.sample(own, n_own)

    # Inject skills from other categories — real resumes are messy
    if noise > 0:
        others = [s for c, v in CATEGORIES.items() if c != cat for s in v["skills"]]
        skills += rng.sample(others, min(int(noise * 4), len(others)))
    rng.shuffle(skills)

    bullets = [
        f"- {rng.choice(spec['verbs'])} {rng.choice(spec['objects'])} "
        f"using {rng.choice(own)} and {rng.choice(own)}."
        for _ in range(rng.randint(2, 4))
    ]

    return "\n".join([
        "Summary",
        f"Practitioner with {rng.randint(1, 9)} years of experience delivering "
        f"{rng.choice(spec['objects'])}.",
        "",
        "Skills",
        ", ".join(skills),
        "",
        "Experience",
        *bullets,
        "",
        "Projects",
        f"- Personal project applying {rng.choice(own)} to {rng.choice(spec['objects'])}.",
        "",
        "Education",
        f"{rng.choice(DEGREES)}, {rng.choice(UNIVERSITIES)}",
    ])


def _job_text(rng: random.Random, cat: str, paraphrase_rate: float = 0.7) -> tuple[str, str]:
    """Build a JD that mostly PARAPHRASES its requirements.

    paraphrase_rate controls how often a skill is described rather than named.
    At 0.0 this degenerates into keyword matching (every lexical baseline wins);
    at 1.0 only semantic methods can succeed. 0.7 is a realistic middle.
    """
    spec = CATEGORIES[cat]
    title = rng.choice(spec["titles"])
    required = rng.sample(spec["skills"], min(5, len(spec["skills"])))

    described = [
        PARAPHRASE.get(s, s) if rng.random() < paraphrase_rate else s
        for s in required
    ]

    # The JD does NOT restate the resume's title or reuse its verb/object
    # phrasing — those would be lexical giveaways.
    text = (
        "About the role\n\n"
        f"Our team is hiring someone to {rng.choice(spec['jd_needs'])}.\n\n"
        f"You should bring hands-on depth in {', '.join(described[:-1])}, "
        f"and {described[-1]}.\n"
        "Strong communication and stakeholder management skills are essential."
    )
    return title, text


def generate(out_dir: str | Path, n_per_category: int = 20, seed: int = 42,
             noise: float = 0.45, paraphrase_rate: float = 0.7) -> None:
    rng = random.Random(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    resumes, jobs, qrels = [], [], []

    for cat in CATEGORIES:
        for i in range(n_per_category):
            rid = f"{cat}_r{i:03d}"
            resumes.append({
                "resume_id": rid,
                "candidate_id": f"cand_{cat}_{i:03d}",   # 1:1 here; real data may differ
                "category": cat,
                "text": _resume_text(rng, cat, noise),
            })

    for cat in CATEGORIES:
        for j in range(4):
            jid = f"{cat}_j{j:02d}"
            title, text = _job_text(rng, cat, paraphrase_rate)
            jobs.append({"job_id": jid, "category": cat, "title": title, "text": text})

            # PROXY LABELS, graded:
            #   3 = same category, 1 = related domain, 0 = unrelated.
            # Still proxy labels, not human judgements — say so when quoting.
            for r in resumes:
                if r["category"] == cat:
                    rel = 3
                else:
                    rel = RELATED.get((r["category"], cat), 0)
                if rel:
                    qrels.append({"job_id": jid, "resume_id": r["resume_id"], "relevance": rel})

    with (out / "resumes.jsonl").open("w", encoding="utf-8") as fh:
        for r in resumes:
            fh.write(json.dumps(r) + "\n")
    with (out / "jobs.jsonl").open("w", encoding="utf-8") as fh:
        for j in jobs:
            fh.write(json.dumps(j) + "\n")
    with (out / "qrels.csv").open("w", encoding="utf-8") as fh:
        fh.write("job_id,resume_id,relevance\n")
        for q in qrels:
            fh.write(f"{q['job_id']},{q['resume_id']},{q['relevance']}\n")

    print(f"Wrote {len(resumes)} resumes, {len(jobs)} jobs, {len(qrels)} judgements -> {out}")


if __name__ == "__main__":
    generate("data/sample")
