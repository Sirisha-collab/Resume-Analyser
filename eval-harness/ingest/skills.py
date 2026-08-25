"""
Skill extraction using YOUR production constants.

Imports TECH_SKILLS / SKILL_SYNONYMS from backend/utils/constants.py so the
harness sees skills exactly the way your app does. Falls back to a bundled
copy when the backend isn't importable (CI, a standalone checkout).

    from ingest.skills import extract_skills, SOURCE
    skills = extract_skills("Built ML pipelines with PyTorch and AWS")
    # -> {'machine learning', 'pytorch', 'amazon web services'}

WHY THIS BEATS A GENERIC TOKENISER
  1. Multi-word skills survive: "machine learning", "power bi", "spring boot"
     are single concepts, not word pairs.
  2. Synonyms normalise: a resume saying "ML" matches a JD saying
     "machine learning". Plain tokenisation misses that entirely.
  3. Punctuation-heavy names work: "c++", "c#", ".net", "node.js".

⚠️  CIRCULARITY WARNING
  If you label relevance with these constants AND score with them (your ATS
  or Jaccard layer), you are grading a scorer against itself. Use these
  labels to judge your SEMANTIC layer. To judge the keyword layer, label
  with an independent source (--strategy llm, or human labels).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# ----------------------------------------------------------------------
# Try the real backend constants first
# ----------------------------------------------------------------------
SOURCE = "fallback"
TECH_SKILLS: set[str] = set()
SKILL_SYNONYMS: dict[str, str] = {}


def _try_import_backend() -> bool:
    """Look for backend/utils/constants.py in the usual relative locations."""
    here = Path(__file__).resolve()
    candidates = [
        here.parent.parent.parent / "backend",     # repo/eval/ingest -> repo/backend
        here.parent.parent / "backend",
        Path.cwd().parent / "backend",
        Path.cwd() / "backend",
    ]
    for c in candidates:
        if (c / "utils" / "constants.py").exists():
            if str(c) not in sys.path:
                sys.path.insert(0, str(c))
            try:
                from utils.constants import TECH_SKILLS as TS, SKILL_SYNONYMS as SS
                TECH_SKILLS.update(TS)
                SKILL_SYNONYMS.update(SS)
                return True
            except Exception:
                continue
    return False


if _try_import_backend():
    SOURCE = "backend/utils/constants.py"
else:
    # Mirror of your constants so the harness runs standalone.
    TECH_SKILLS = {
        "python", "java", "javascript", "typescript", "c", "c++", "c#", "php",
        "ruby", "go", "swift", "kotlin", "r",
        "react", "angular", "vue", "html", "css", "bootstrap", "tailwind",
        "nodejs", "express", "django", "flask", ".net", "spring", "spring boot",
        "sql", "mysql", "postgresql", "mongodb", "oracle", "sqlite",
        "aws", "azure", "gcp", "docker", "kubernetes",
        "machine learning", "deep learning", "nlp", "tensorflow",
        "pytorch", "opencv", "artificial intelligence",
        "power bi", "tableau", "excel", "pandas", "numpy",
        "git", "github", "jira", "linux", "postman", "figma",
        "rest api", "graphql",
    }
    SKILL_SYNONYMS = {
        "ml": "machine learning", "ai": "artificial intelligence",
        "dl": "deep learning", "ds": "data science", "js": "javascript",
        "py": "python", "db": "database", "pm": "project management",
        "nlp": "natural language processing", "gcp": "google cloud platform",
        "aws": "amazon web services", "az": "azure",
    }

# Canonical vocabulary = skills plus every synonym target
VOCAB: set[str] = set(TECH_SKILLS) | set(SKILL_SYNONYMS.values())

# ----------------------------------------------------------------------
# Matching
# ----------------------------------------------------------------------
# Longest-first so "spring boot" wins over "spring", and "c++" over "c".
_SORTED = sorted(VOCAB, key=len, reverse=True)
_ALTERNATION = "|".join(re.escape(s) for s in _SORTED)

# Skills whose names are too short for a plain word-boundary match — bare "c"
# or "r" would fire on ordinary prose. These require a list-like delimiter
# (comma, pipe, slash, newline, bullet) on at least one side.
_SHORT_SKILLS = {s for s in VOCAB if len(s) <= 2}

# NOTE the (?:...) group. Without it, alternation binds looser than the
# lookarounds and only the first/last alternatives get boundary guards —
# every skill in between then matches inside other words.
_SKILL_RE = re.compile(
    r"(?<![a-z0-9+#.])(?:" + _ALTERNATION + r")(?![a-z0-9+#])",
    re.IGNORECASE,
)

_SYN_RE = re.compile(
    r"(?<![a-z0-9])(" + "|".join(re.escape(k) for k in
                                 sorted(SKILL_SYNONYMS, key=len, reverse=True))
    + r")(?![a-z0-9])",
    re.IGNORECASE,
) if SKILL_SYNONYMS else None

_DELIM = re.compile(r"[,\|/\n\t;•·]")


def expand_synonyms(text: str) -> str:
    """Rewrite abbreviations to their canonical form BEFORE matching.

    'Built ML models' -> 'Built machine learning models', so a JD asking for
    'machine learning' matches a resume that only ever wrote 'ML'.
    """
    if _SYN_RE is None:
        return text
    return _SYN_RE.sub(lambda m: SKILL_SYNONYMS[m.group(0).lower()], text)


def _short_skill_ok(text: str, start: int, end: int) -> bool:
    """1-2 char skills ('c', 'r', 'go') need list context on BOTH sides.

    A bare 'r' in prose is the letter r; 'R' in 'Python, R, SQL' is the
    language. Requiring a delimiter either side is what separates them.
    Requiring only one side still lets ordinary words through.
    """
    before = text[max(0, start - 2):start].strip()
    after = text[end:end + 2].strip()
    left_ok = start == 0 or bool(_DELIM.search(before)) or before == ""
    right_ok = end >= len(text) or bool(_DELIM.search(after)) or after == ""
    return left_ok and right_ok


def extract_skills(text: str) -> set[str]:
    """Canonical skill set found in the text."""
    expanded = expand_synonyms(text.lower())
    found = set()
    for m in _SKILL_RE.finditer(expanded):
        skill = m.group(0).lower()
        if skill in _SHORT_SKILLS and not _short_skill_ok(expanded, m.start(), m.end()):
            continue
        found.add(skill)
    return found


def skill_overlap(resume_text: str, job_text: str) -> tuple[set, set, set]:
    """Returns (matched, missing, extra) skill sets."""
    r, j = extract_skills(resume_text), extract_skills(job_text)
    return r & j, j - r, r - j


def coverage(resume_text: str, job_text: str) -> float:
    """Fraction of the job's required skills present in the resume."""
    matched, missing, _ = skill_overlap(resume_text, job_text)
    denom = len(matched) + len(missing)
    return len(matched) / denom if denom else 0.0


def describe() -> str:
    return (f"skills: {len(TECH_SKILLS)} terms, {len(SKILL_SYNONYMS)} synonyms "
            f"(source: {SOURCE})")
