"""
Systems under test.

Every scorer implements the same interface, so adding your real Resume Analyser
pipeline is a ~20 line class (see RESUME_ANALYSER_ADAPTER at the bottom).

Ordering matters for interpretation:
  RandomScorer      -> the FLOOR. If your model can't beat this, nothing works.
  JaccardScorer     -> what a naive keyword ATS effectively does.
  BM25Scorer        -> strong classical lexical baseline.
  TfidfCosineScorer -> strong classical semantic-ish baseline.
  Embedding*        -> your actual contribution.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Protocol

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class Scorer(Protocol):
    name: str
    def fit(self, corpus: list[str]) -> None: ...
    def score(self, job_text: str, resume_texts: list[str]) -> np.ndarray: ...


_TOKEN_RE = re.compile(r"[a-z0-9+#.]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


# ----------------------------------------------------------------------
# 1. Random — the floor
# ----------------------------------------------------------------------
class RandomScorer:
    """Proves the task is non-trivial. Always report this.

    If a system scores near random, the metric or the labels are broken —
    and it's better to find that out here than in a viva.
    """
    name = "Random (floor)"

    def __init__(self, seed: int = 42):
        self._rng = np.random.default_rng(seed)

    def fit(self, corpus: list[str]) -> None:
        pass

    def score(self, job_text: str, resume_texts: list[str]) -> np.ndarray:
        return self._rng.random(len(resume_texts))


# ----------------------------------------------------------------------
# 2. Jaccard skill overlap — the naive ATS
# ----------------------------------------------------------------------
DEFAULT_SKILL_VOCAB = {
    "python", "java", "javascript", "typescript", "sql", "c++", "go", "rust",
    "react", "angular", "vue", "node.js", "django", "flask", "fastapi", "spring",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "jenkins", "ci/cd",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "kafka",
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "spark", "hadoop",
    "tableau", "power", "excel", "looker", "dbt", "airflow",
    "machine", "learning", "nlp", "deep", "statistics", "regression",
    "figma", "sketch", "photoshop", "illustrator", "wireframing", "prototyping",
    "seo", "sem", "analytics", "hubspot", "salesforce", "copywriting",
    "communication", "leadership", "agile", "scrum", "stakeholder",
}


class JaccardScorer:
    """Set overlap between skills found in the resume and skills in the job.

    This is the honest representation of what a keyword-matching ATS does,
    and it is the baseline your semantic model must beat to justify itself.
    """
    name = "Jaccard keyword overlap"

    def __init__(self, vocab: set[str] | None = None):
        self.vocab = vocab or DEFAULT_SKILL_VOCAB

    def fit(self, corpus: list[str]) -> None:
        pass

    def _skills(self, text: str) -> set[str]:
        return set(tokenize(text)) & self.vocab

    def score(self, job_text: str, resume_texts: list[str]) -> np.ndarray:
        job_skills = self._skills(job_text)
        out = np.zeros(len(resume_texts))
        if not job_skills:
            return out
        for i, rt in enumerate(resume_texts):
            rs = self._skills(rt)
            union = job_skills | rs
            out[i] = len(job_skills & rs) / len(union) if union else 0.0
        return out


# ----------------------------------------------------------------------
# 3. BM25 — strong lexical baseline
# ----------------------------------------------------------------------
class BM25Scorer:
    """Okapi BM25. Implemented directly so the formula is inspectable.

        score = sum_t IDF(t) * (f(t,d) * (k1+1)) / (f(t,d) + k1*(1-b+b*|d|/avgdl))

    Term saturation (k1) stops a resume winning by repeating one keyword;
    length normalisation (b) stops long resumes winning by sheer volume.
    Both are failure modes of raw TF that matter for resumes specifically.
    """
    name = "BM25"

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self._idf: dict[str, float] = {}
        self._avgdl: float = 0.0

    def fit(self, corpus: list[str]) -> None:
        docs = [tokenize(d) for d in corpus]
        n = len(docs)
        self._avgdl = float(np.mean([len(d) for d in docs])) if docs else 0.0

        df: Counter = Counter()
        for d in docs:
            df.update(set(d))
        # Standard BM25 IDF with +0.5 smoothing, floored at a small positive value
        self._idf = {
            t: max(math.log((n - c + 0.5) / (c + 0.5) + 1.0), 1e-6)
            for t, c in df.items()
        }

    def score(self, job_text: str, resume_texts: list[str]) -> np.ndarray:
        query = tokenize(job_text)
        out = np.zeros(len(resume_texts))
        for i, rt in enumerate(resume_texts):
            doc = tokenize(rt)
            freqs = Counter(doc)
            dl = len(doc)
            norm = self.k1 * (1 - self.b + self.b * dl / (self._avgdl or 1.0))
            s = 0.0
            for t in query:
                f = freqs.get(t, 0)
                if f:
                    s += self._idf.get(t, 0.0) * (f * (self.k1 + 1)) / (f + norm)
            out[i] = s
        return out


# ----------------------------------------------------------------------
# 4. TF-IDF cosine
# ----------------------------------------------------------------------
class TfidfCosineScorer:
    """Fitted on the TRAINING corpus only — never on test text.

    Fitting the vectoriser on all data before splitting leaks test vocabulary
    and IDF statistics into training. It is a subtle and very common bug.
    """
    name = "TF-IDF cosine"

    def __init__(self, ngram_range=(1, 2), min_df=1):
        self._vec = TfidfVectorizer(
            ngram_range=ngram_range, min_df=min_df, stop_words="english", sublinear_tf=True
        )
        self._fitted = False

    def fit(self, corpus: list[str]) -> None:
        self._vec.fit(corpus)
        self._fitted = True

    def score(self, job_text: str, resume_texts: list[str]) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("TfidfCosineScorer.fit() must be called first")
        q = self._vec.transform([job_text])
        d = self._vec.transform(resume_texts)
        return cosine_similarity(q, d)[0]


# ----------------------------------------------------------------------
# 5 & 6. Embedding scorers (optional — require sentence-transformers)
# ----------------------------------------------------------------------
def embeddings_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


class EmbeddingScorer:
    """Whole-document BERT embedding + cosine similarity.

    This is the 'no chunking' arm of the ablation.
    """
    name = "BERT whole-doc"

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_name)

    def fit(self, corpus: list[str]) -> None:
        pass                                    # nothing to fit; pretrained

    def _embed(self, texts: list[str]) -> np.ndarray:
        return self._model.encode(
            texts, batch_size=32, normalize_embeddings=True, convert_to_numpy=True
        )

    def score(self, job_text: str, resume_texts: list[str]) -> np.ndarray:
        q = self._embed([job_text])[0]
        d = self._embed(resume_texts)
        return d @ q                            # normalised, so dot == cosine


SECTION_WEIGHTS = {"skills": 0.45, "experience": 0.35, "projects": 0.15, "education": 0.05}

SECTION_HEADERS = {
    "skills": ["skills", "technical skills", "core competencies", "technologies"],
    "experience": ["experience", "work experience", "employment", "professional experience"],
    "education": ["education", "academic", "qualifications"],
    "projects": ["projects", "personal projects", "selected projects"],
}


def segment_resume(text: str) -> dict[str, str]:
    """Split a resume into semantic sections; fall back to a single blob."""
    sections: dict[str, list[str]] = {}
    current = "preamble"
    for line in text.splitlines():
        stripped = line.strip().lower().rstrip(":")
        matched = next(
            (canon for canon, variants in SECTION_HEADERS.items()
             if stripped in variants),
            None,
        )
        if matched:
            current = matched
            continue
        sections.setdefault(current, []).append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items() if "".join(v).strip()}


class SectionWeightedEmbeddingScorer(EmbeddingScorer):
    """THE ABLATION ARM: section-aware weighting on top of BERT embeddings.

    Comparing this against EmbeddingScorer is what proves the chunking
    strategy earned its place — rather than just asserting that it did.
    """
    name = "BERT + section weighting"

    def score(self, job_text: str, resume_texts: list[str]) -> np.ndarray:
        q = self._embed([job_text])[0]
        out = np.zeros(len(resume_texts))

        for i, rt in enumerate(resume_texts):
            sections = segment_resume(rt)
            weighted = [(SECTION_WEIGHTS.get(n, 0.0), t)
                        for n, t in sections.items() if SECTION_WEIGHTS.get(n, 0.0) > 0]
            if not weighted:
                out[i] = float(self._embed([rt])[0] @ q)   # unstructured fallback
                continue
            vecs = self._embed([t for _, t in weighted])
            w = np.array([wt for wt, _ in weighted])
            out[i] = float(np.sum(w * (vecs @ q)) / w.sum())
        return out


# ----------------------------------------------------------------------
# Adapter template — plug in YOUR real pipeline here
# ----------------------------------------------------------------------
RESUME_ANALYSER_ADAPTER = '''
class ResumeAnalyserScorer:
    """Wrap your real production pipeline so it is measured identically
    to every baseline. Copy into scorers.py and register in run_eval.py."""
    name = "Resume Analyser (full)"

    def __init__(self):
        from app.scoring import score_resume_against_job   # your code
        self._score = score_resume_against_job

    def fit(self, corpus): pass

    def score(self, job_text, resume_texts):
        import numpy as np
        return np.array([self._score(rt, job_text)["job_fit_pct"] for rt in resume_texts])
'''
