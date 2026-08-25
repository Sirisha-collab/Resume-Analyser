#!/usr/bin/env python3
"""
Inspect your existing artifacts and report which are safe to use as
EVALUATION INPUT versus which are model output.

    python -m ingest.inspect_artifacts /path/to/your/data

The rule it enforces:
    Evaluation input = RAW TEXT + LABELS.
    Anything your model produced (embeddings, cached scores, fitted models)
    is a RESULT, not a fixture. Feeding it back in makes the harness
    measure the model against itself.
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

VERDICT = {
    "input": "\u2705 USE  ",
    "maybe": "\u26a0\ufe0f  CHECK",
    "output": "\u274c SKIP ",
}


def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.0f}TB"


def inspect_pdf(path: Path) -> tuple[str, str]:
    try:
        import pdfplumber
    except ImportError:
        return "input", "PDF resume (install pdfplumber to extract)"
    try:
        with pdfplumber.open(path) as pdf:
            pages = len(pdf.pages)
            text = (pdf.pages[0].extract_text() or "").strip()
        if not text:
            return "maybe", (
                f"{pages}p but NO extractable text \u2014 likely a SCANNED image. "
                "Needs OCR or it will score as an empty document."
            )
        return "input", f"{pages}p, {len(text)} chars on p1 \u2014 raw text, good"
    except Exception as e:
        return "maybe", f"could not open: {type(e).__name__}"


def inspect_text(path: Path) -> tuple[str, str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception as e:
        return "maybe", f"unreadable: {e}"
    if not text:
        return "maybe", "empty file"
    return "input", f"{len(text)} chars, {len(text.splitlines())} lines \u2014 raw text, good"


def inspect_json(path: Path) -> tuple[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return "maybe", f"invalid JSON: {e}"

    # Heuristics: does it look like a manifest, or like model output?
    sample = data[:3] if isinstance(data, list) else data
    blob = json.dumps(sample)[:4000].lower()

    embedding_markers = ("embedding", "vector", "dense", "encoded")
    score_markers = ("ats_score", "ml_score", "dl_rank", "job_fit", "similarity", "score")
    manifest_markers = ("path", "file", "filename", "category", "label", "title", "id")

    has_emb = any(m in blob for m in embedding_markers)
    has_score = any(m in blob for m in score_markers)
    has_manifest = any(m in blob for m in manifest_markers)

    n = len(data) if isinstance(data, (list, dict)) else 0

    if has_emb:
        return "output", (
            f"{n} entries, contains EMBEDDINGS \u2014 model output. "
            "Do not use as eval input; re-derive from raw text."
        )
    if has_score and not has_manifest:
        return "output", (
            f"{n} entries, contains SCORES \u2014 model output, not ground truth."
        )
    if has_manifest:
        keys = list(sample[0].keys())[:8] if isinstance(sample, list) and sample and isinstance(sample[0], dict) \
            else (list(sample.keys())[:8] if isinstance(sample, dict) else [])
        return "maybe", (
            f"{n} entries, looks like a MANIFEST (keys: {keys}). "
            "Usable for filenames/categories \u2014 but any parsed text inside is model output."
        )
    return "maybe", f"{n} entries \u2014 inspect manually"


def inspect_pickle(path: Path) -> tuple[str, str]:
    # NOTE: only unpickle files YOU created. Pickle executes arbitrary code.
    try:
        with path.open("rb") as fh:
            obj = pickle.load(fh)
    except Exception as e:
        return "output", f"could not load ({type(e).__name__}) \u2014 treat as model artifact"

    t = type(obj).__name__
    mod = type(obj).__module__

    if mod.startswith("sklearn"):
        return "output", (
            f"{mod}.{t} \u2014 a TRAINED MODEL. This is the system under test, "
            "not data. Wrap it in a Scorer instead."
        )
    if t in ("ndarray",) or "numpy" in mod:
        shape = getattr(obj, "shape", "?")
        return "output", (
            f"numpy array {shape} \u2014 almost certainly cached EMBEDDINGS. "
            "Not eval input."
        )
    if isinstance(obj, dict):
        keys = list(obj.keys())[:6]
        return "maybe", f"dict with keys {keys} \u2014 inspect; may be an id map (usable) or vectors (not)"
    if isinstance(obj, list):
        return "maybe", f"list of {len(obj)} \u2014 inspect first element type: {type(obj[0]).__name__ if obj else 'empty'}"
    return "maybe", f"{mod}.{t} \u2014 inspect manually"


def inspect_faiss(path: Path) -> tuple[str, str]:
    return "output", (
        "FAISS index \u2014 embeddings produced by YOUR model. Using it as eval "
        "input forces every baseline to see the world through your model's "
        "representation, which makes the comparison meaningless. "
        "Legitimate use: production-parity check only."
    )


DISPATCH = {
    ".pdf": inspect_pdf,
    ".txt": inspect_text,
    ".md": inspect_text,
    ".json": inspect_json,
    ".jsonl": lambda p: ("maybe", "JSONL \u2014 inspect; may already be harness format"),
    ".pkl": inspect_pickle,
    ".pickle": inspect_pickle,
    ".joblib": inspect_pickle,
    ".index": inspect_faiss,
    ".faiss": inspect_faiss,
    ".bin": inspect_faiss,
}


def main(root: str) -> int:
    base = Path(root)
    if not base.exists():
        print(f"Path not found: {base}", file=sys.stderr)
        return 1

    files = sorted(p for p in base.rglob("*") if p.is_file())
    if not files:
        print(f"No files under {base}")
        return 1

    print(f"\nInspecting {len(files)} file(s) under {base}\n")
    print(f"{'VERDICT':<9} {'SIZE':>7}  {'FILE':<42} NOTES")
    print("-" * 118)

    counts = {"input": 0, "maybe": 0, "output": 0}
    usable_pdfs, usable_txt = [], []

    for p in files:
        fn = DISPATCH.get(p.suffix.lower())
        if fn is None:
            continue
        verdict, note = fn(p)
        counts[verdict] += 1
        if verdict == "input":
            (usable_pdfs if p.suffix.lower() == ".pdf" else usable_txt).append(p)
        rel = str(p.relative_to(base))
        rel = rel if len(rel) <= 42 else "..." + rel[-39:]
        print(f"{VERDICT[verdict]:<9} {_human(p.stat().st_size):>7}  {rel:<42} {note}")

    print("-" * 118)
    print(f"\n  {counts['input']} usable as eval input | "
          f"{counts['maybe']} need checking | {counts['output']} are model output\n")

    print(f"  Resumes (PDF) ready:  {len(usable_pdfs)}")
    print(f"  Text files ready:     {len(usable_txt)}")

    print("\nNEXT STEP")
    if not usable_pdfs:
        print("  No extractable PDFs found. If yours are scanned images, you need OCR first.")
    else:
        print("  python -m ingest.build_dataset --resumes <pdf_dir> --jobs <jd_dir> --out data/real")
    print("  ...then label:  python -m ingest.make_qrels --data data/real\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
