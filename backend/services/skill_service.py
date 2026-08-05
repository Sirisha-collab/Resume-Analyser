import re
from typing import List, Set, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from utils.constants import TECH_SKILLS, SKILL_SYNONYMS
from utils.helpers import similar
from services.ats_service import (
    get_ats_breakdown, get_semantic_coverage,
    get_structure_score, get_priority_skill_depth,
    SEMANTIC_WEIGHT, STRUCTURE_WEIGHT,
    BASE_POINTS, PRIORITY_POINTS,
)
from typing import Dict, List, Sequence, Tuple

_SKILL_ALTERNATION = "|".join(
    re.escape(skill) for skill in sorted(TECH_SKILLS, key=len, reverse=True)
)

SKILL_PATTERN = re.compile(
    rf"(?<![a-z0-9+#.])(?:{_SKILL_ALTERNATION})(?![a-z0-9+#])"
)

WORD_PATTERN = re.compile(r"\.?[a-z0-9][a-z0-9+#.]*")

ENABLE_FUZZY_MATCH = False
FUZZY_THRESHOLD = 0.85
FUZZY_MIN_LENGTH = 5

LOW_SCORE_THRESHOLD = 50
MAX_SUGGESTED_SKILLS = 5


def _normalize(skill: str) -> str:
    """react.js / reactjs / React.JS -> reactjs"""
    return re.sub(r"[^a-z0-9]", "", skill.lower())


def get_keywords(text: str) -> Set[str]:
    text = (text or "").lower()
    found_skills = set()

    found_skills.update(SKILL_PATTERN.findall(text))

    for raw in WORD_PATTERN.findall(text):
        word = raw.rstrip(".")
        word = SKILL_SYNONYMS.get(word, word)
        if word in TECH_SKILLS:
            found_skills.add(word)

    return found_skills


def analyze_resume(
    resume_text: str,
    job_desc: str,
    required_skills: Sequence[str] = (),
    matched_skills: Sequence[str] = (),
) -> float:
    if required_skills:
        return get_ats_breakdown(
            resume_text, job_desc, required_skills, matched_skills
        )["score"]

    semantic, _ = get_semantic_coverage(resume_text, job_desc)
    structure, _ = get_structure_score(resume_text)
    depth, depth_detail, _ = get_priority_skill_depth(resume_text, job_desc)

    weight_sum = SEMANTIC_WEIGHT + STRUCTURE_WEIGHT
    base = (semantic * SEMANTIC_WEIGHT + structure * STRUCTURE_WEIGHT) / weight_sum

    total = base * BASE_POINTS + depth * PRIORITY_POINTS if depth_detail else base * 100.0
    return round(max(0.0, min(100.0, total)), 2)


def _fuzzy_match(job_skill: str, resume_words: Set[str]) -> bool:
    if len(job_skill) < FUZZY_MIN_LENGTH:
        return False
    return any(
        len(resume_skill) >= FUZZY_MIN_LENGTH
        and similar(job_skill, resume_skill) >= FUZZY_THRESHOLD
        for resume_skill in resume_words
    )


def skill_gap(resume_text: str, job_text: str) -> Tuple[List[str], List[str]]:
    resume_words = get_keywords(resume_text)
    job_words = get_keywords(job_text)
    resume_normalized = {_normalize(skill) for skill in resume_words}

    matched, missing = [], []
    for job_skill in sorted(job_words):         
        if job_skill in resume_words or _normalize(job_skill) in resume_normalized:
            matched.append(job_skill)
        elif ENABLE_FUZZY_MATCH and _fuzzy_match(job_skill, resume_words):
            matched.append(job_skill)
        else:
            missing.append(job_skill)

    return matched, missing


def generate_suggestions(score: float, missing_skills: List[str]) -> List[str]:
    suggestions = []

    if score < LOW_SCORE_THRESHOLD:
        suggestions.append("Your resume has a low match score.")

    if missing_skills:
        top = sorted(missing_skills)[:MAX_SUGGESTED_SKILLS]
        suggestions.append(f"Add these skills: {', '.join(top)}")

    return suggestions