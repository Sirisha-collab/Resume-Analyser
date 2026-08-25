#!/usr/bin/env python3
"""
Convert real PDF resumes + JD text files into the harness dataset format.

    python -m ingest.build_dataset \
        --resumes /path/to/resumes \
        --jobs    /path/to/job_descriptions \
        --out     data/real

Category inference: if your PDFs live in per-role subfolders, e.g.

    resumes/
      data_analyst/asha_menon.pdf
      backend_engineer/rahul_k.pdf

...the folder name becomes the category, which lets make_qrels bootstrap
proxy labels automatically. Flat directories work too; you just have to
label by hand.

IMPORTANT: this writes RAW TEXT only. It never touches your FAISS index,
.pkl files, or cached embeddings — those are model output, and feeding them
back into evaluation makes the harness measure your model against itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

# ----------------------------------------------------------------------
# Section detection — mirrors harness/scorers.py so the section-weighted
# scorer can use the same segmentation at eval time.
# ----------------------------------------------------------------------
SECTION_HEADERS = {
    "skills": ["skills", "technical skills", "core competencies", "technologies",
               "technical expertise", "key skills"],
    "experience": ["experience", "work experience", "employment", "professional experience",
                   "work history", "career history"],
    "education": ["education", "academic", "qualifications", "academic background"],
    "projects": ["projects", "personal projects", "selected projects", "key projects"],
    "summary": ["summary", "profile", "objective", "about me", "professional summary"],
}


def extract_pdf_text(path: Path) -> str:
    """Extract text, preserving line structure so section headers survive.

    pdfplumber (not PyPDF2) because it keeps layout — multi-column resumes
    get mangled otherwise, and layout is what section detection relies on.
    """
    import pdfplumber

    parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            if txt.strip():
                parts.append(txt)
    return "\n".join(parts)


def extract_docx_text(path: Path) -> str:
    from docx import Document
    return "\n".join(p.text for p in Document(str(path)).paragraphs)


def segment(text: str) -> dict[str, str]:
    """Split into semantic sections; returns {} if no headers are detected."""
    sections: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        probe = line.strip().lower().rstrip(":").strip()
        if 0 < len(probe) <= 40:
            matched = next(
                (canon for canon, variants in SECTION_HEADERS.items() if probe in variants),
                None,
            )
            if matched:
                current = matched
                sections.setdefault(current, [])
                continue
        if current:
            sections[current].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items() if "".join(v).strip()}


def clean(text: str) -> str:
    """Collapse runaway whitespace without destroying line structure."""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ----------------------------------------------------------------------
# Light PII redaction (recommended before embedding — see fairness note)
# ----------------------------------------------------------------------
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
URL_RE = re.compile(r"https?://\S+|\bwww\.\S+")


def redact(text: str) -> str:
    """Strip direct identifiers.

    Two reasons: (1) your eval data is PII and shouldn't sit in a repo,
    (2) names and contact details are a known source of bias in resume
    scoring — removing them before embedding is a cheap mitigation.

    This does NOT remove names in body text. Full name redaction needs NER.
    """
    text = EMAIL_RE.sub("[EMAIL]", text)
    text = PHONE_RE.sub("[PHONE]", text)
    text = URL_RE.sub("[URL]", text)
    return text


def stable_id(path: Path, prefix: str) -> str:
    h = hashlib.sha1(path.name.encode()).hexdigest()[:8]
    return f"{prefix}_{h}"


# ----------------------------------------------------------------------
def build(resume_dir: Path, job_dir: Path, out_dir: Path,
          do_redact: bool, min_chars: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---------------- resumes ----------------
    resume_files = [
        p for p in sorted(resume_dir.rglob("*"))
        if p.suffix.lower() in {".pdf", ".docx", ".txt"}
    ]
    if not resume_files:
        raise SystemExit(f"No .pdf/.docx/.txt resumes found under {resume_dir}")

    resumes, skipped = [], []
    for p in resume_files:
        try:
            if p.suffix.lower() == ".pdf":
                raw = extract_pdf_text(p)
            elif p.suffix.lower() == ".docx":
                raw = extract_docx_text(p)
            else:
                raw = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            skipped.append((p.name, f"{type(e).__name__}: {e}"))
            continue

        text = clean(raw)
        if len(text) < min_chars:
            # Nearly always a scanned image with no text layer.
            skipped.append((p.name, f"only {len(text)} chars — scanned PDF? needs OCR"))
            continue
        if do_redact:
            text = redact(text)

        # Category from parent folder when the layout is resumes/<category>/file.pdf
        category = p.parent.name if p.parent != resume_dir else ""

        resumes.append({
            "resume_id": stable_id(p, "r"),
            # One resume per candidate by default. If you have multiple resumes
            # from the same person, EDIT candidate_id so they group together —
            # otherwise the train/test split will leak.
            "candidate_id": stable_id(p, "c"),
            "category": category,
            "text": text,
            "sections": segment(text),
            "source_file": p.name,
        })

    # ---------------- jobs ----------------
    job_files = [
        p for p in sorted(job_dir.rglob("*"))
        if p.suffix.lower() in {".txt", ".md", ".json"}
    ]
    if not job_files:
        raise SystemExit(f"No .txt/.md/.json job descriptions found under {job_dir}")

    jobs = []
    for p in job_files:
        if p.suffix.lower() == ".json":
            data = json.loads(p.read_text(encoding="utf-8"))
            text = data.get("description_text") or data.get("text") or ""
            title = data.get("title", p.stem)
        else:
            text = p.read_text(encoding="utf-8", errors="replace")
            title = p.stem.replace("_", " ").title()
        text = clean(text)
        if not text:
            skipped.append((p.name, "empty job description"))
            continue
        jobs.append({
            "job_id": stable_id(p, "j"),
            "category": p.parent.name if p.parent != job_dir else "",
            "title": title,
            "text": text,
            "source_file": p.name,
        })

    # ---------------- write ----------------
    with (out_dir / "resumes.jsonl").open("w", encoding="utf-8") as fh:
        for r in resumes:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (out_dir / "jobs.jsonl").open("w", encoding="utf-8") as fh:
        for j in jobs:
            fh.write(json.dumps(j, ensure_ascii=False) + "\n")

    # ---------------- report ----------------
    print(f"\n  resumes written : {len(resumes)}")
    print(f"  jobs written    : {len(jobs)}")
    n_sectioned = sum(1 for r in resumes if r["sections"])
    print(f"  sections found  : {n_sectioned}/{len(resumes)} "
          f"({n_sectioned/max(len(resumes),1)*100:.0f}%)")
    cats = {r["category"] for r in resumes if r["category"]}
    print(f"  categories      : {sorted(cats) if cats else '(none — flat directory)'}")

    if skipped:
        print(f"\n  ⚠️  skipped {len(skipped)} file(s):")
        for name, why in skipped[:10]:
            print(f"      {name}: {why}")

    print(f"\n  → {out_dir}/resumes.jsonl")
    print(f"  → {out_dir}/jobs.jsonl")
    print(f"\n  qrels.csv NOT created — you must label relevance next:")
    print(f"      python -m ingest.make_qrels --data {out_dir}\n")

    if not cats:
        print("  NOTE: no category subfolders detected, so proxy labels can't be")
        print("        bootstrapped. You'll be labelling by hand.\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build harness dataset from real files")
    ap.add_argument("--resumes", required=True, help="directory of PDF/DOCX/TXT resumes")
    ap.add_argument("--jobs", required=True, help="directory of JD text files")
    ap.add_argument("--out", default="data/real")
    ap.add_argument("--no-redact", action="store_true",
                    help="keep emails/phones (NOT recommended)")
    ap.add_argument("--min-chars", type=int, default=200,
                    help="below this, treat as a failed extraction")
    a = ap.parse_args()

    build(Path(a.resumes), Path(a.jobs), Path(a.out),
          do_redact=not a.no_redact, min_chars=a.min_chars)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
