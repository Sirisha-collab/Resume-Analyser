#!/usr/bin/env python3
"""
Production parity check — the ONE legitimate use for your FAISS index
and cached .pkl embeddings.

    python -m ingest.parity_check --data data/real \
        --faiss /path/to/resume_index.faiss \
        --idmap /path/to/resume_index.json

WHAT THIS IS NOT:
    It is not an evaluation. It never produces a quality metric.

WHAT IT IS:
    A sanity check that the vectors sitting in your production FAISS index
    still match what your CURRENT code produces from the same raw text.

WHY IT MATTERS:
    Indexes go stale. If you changed the model, the preprocessing, or the
    chunking since the index was built, production is serving results from
    an old representation while your eval measures the new one. You would
    then be reporting numbers your live site does not actually achieve.
    That gap is invisible until someone checks — this checks it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def load_idmap(path: Path) -> dict[int, str]:
    """Map FAISS row position -> your resume_id.

    Accepts either {"0": "r_abc", ...} or [{"id": 0, "resume_id": "r_abc"}, ...]
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return {int(k): str(v) if not isinstance(v, dict) else str(v.get("resume_id", v))
                for k, v in data.items()}
    out = {}
    for i, row in enumerate(data):
        if isinstance(row, dict):
            pos = int(row.get("index", row.get("id", i)))
            out[pos] = str(row.get("resume_id", row.get("path", i)))
        else:
            out[i] = str(row)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Check FAISS index freshness vs current code")
    ap.add_argument("--data", required=True, help="dataset dir (resumes.jsonl)")
    ap.add_argument("--faiss", required=True, help="path to your .faiss/.index file")
    ap.add_argument("--idmap", required=True, help="JSON mapping index position -> resume_id")
    ap.add_argument("--tolerance", type=float, default=0.99,
                    help="min cosine similarity to count as 'matching'")
    ap.add_argument("--sample", type=int, default=25)
    a = ap.parse_args()

    try:
        import faiss
    except ImportError:
        print("faiss-cpu not installed:  pip install faiss-cpu", file=sys.stderr)
        return 1
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("sentence-transformers not installed", file=sys.stderr)
        return 1

    resumes = [json.loads(l) for l in (Path(a.data) / "resumes.jsonl")
               .read_text(encoding="utf-8").splitlines() if l.strip()]
    by_id = {r["resume_id"]: r for r in resumes}

    index = faiss.read_index(a.faiss)
    idmap = load_idmap(Path(a.idmap))
    print(f"  index: {index.ntotal} vectors, dim={index.d}")
    print(f"  idmap: {len(idmap)} entries")
    print(f"  dataset: {len(resumes)} resumes\n")

    # Re-encode with the CURRENT model and compare against the stored vectors
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    positions = [p for p in sorted(idmap) if idmap[p] in by_id][:a.sample]
    if not positions:
        print("  No overlap between idmap and dataset resume_ids.", file=sys.stderr)
        print("  Your index was probably built with different IDs.", file=sys.stderr)
        return 1

    stored = np.vstack([index.reconstruct(int(p)) for p in positions])
    # normalise both sides so the comparison is cosine regardless of how
    # the index was built
    stored = stored / (np.linalg.norm(stored, axis=1, keepdims=True) + 1e-12)

    fresh = model.encode(
        [by_id[idmap[p]]["text"] for p in positions],
        batch_size=32, normalize_embeddings=True, convert_to_numpy=True,
    )

    if stored.shape[1] != fresh.shape[1]:
        print(f"  ❌ DIMENSION MISMATCH: index d={stored.shape[1]}, "
              f"current model d={fresh.shape[1]}")
        print("     Your index was built with a DIFFERENT MODEL. It is stale.")
        print("     Rebuild it before trusting any production result.\n")
        return 2

    sims = np.sum(stored * fresh, axis=1)
    n_match = int(np.sum(sims >= a.tolerance))

    print(f"  compared {len(positions)} vectors")
    print(f"  cosine  min={sims.min():.4f}  mean={sims.mean():.4f}  max={sims.max():.4f}")
    print(f"  matching (>= {a.tolerance}): {n_match}/{len(positions)}\n")

    if n_match == len(positions):
        print("  ✅ Index is FRESH — production vectors match current code.")
        print("     Eval results are representative of what your site serves.\n")
        return 0

    print("  ⚠️  Index is STALE — stored vectors differ from current code.")
    print("     Likely causes: model changed, preprocessing changed, or the")
    print("     index predates your latest parser fix.")
    print("     Rebuild the index, or your eval measures something your")
    print("     live site does not actually do.\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
