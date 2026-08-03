import numpy as np
from typing import List, Tuple

from fastembed import TextEmbedding
from services.skill_service import get_keywords

SEMANTIC_MODEL_NAME = "BAAI/bge-small-en-v1.5"
SEMANTIC_MATCH_THRESHOLD = 0.75

_embedder = None


def get_embedder() -> TextEmbedding:

    global _embedder
    if _embedder is None:
        _embedder = TextEmbedding(model_name=SEMANTIC_MODEL_NAME)
    return _embedder


def _embed(phrases: List[str]) -> np.ndarray:
    vectors = np.array(list(get_embedder().embed(phrases)), dtype=np.float32)
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def ats_simulation(resume_text: str, job_desc: str) -> Tuple[List[str], List[str]]:
    """
    Split JD keywords into two buckets:
      - soft_gaps: rewording fix
      - hard_gaps: real skill gap
    """
    resume_words = set(get_keywords(resume_text or ""))
    job_words = set(get_keywords(job_desc or ""))
    missing = sorted(job_words - resume_words)

    if not missing or not resume_words:
        return [], missing

    resume_vecs = _embed(sorted(resume_words))
    missing_vecs = _embed(missing)

    best_sim = (missing_vecs @ resume_vecs.T).max(axis=1)

    soft_gaps, hard_gaps = [], []
    for term, sim in zip(missing, best_sim):
        (soft_gaps if sim >= SEMANTIC_MATCH_THRESHOLD else hard_gaps).append(term)

    return soft_gaps, hard_gaps