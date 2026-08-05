import re
import numpy as np
from collections import OrderedDict
from typing import Dict, List, Optional, Sequence, Tuple

from fastembed import TextEmbedding

SEMANTIC_MODEL_NAME = "BAAI/bge-small-en-v1.5"

# ---------------------------------------------------------------- weighting --
SKILL_WEIGHT = 0.55
SEMANTIC_WEIGHT = 0.30
STRUCTURE_WEIGHT = 0.15

PRIORITY_POINTS = 15.0
BASE_POINTS = 100.0 - PRIORITY_POINTS

assert abs(SKILL_WEIGHT + SEMANTIC_WEIGHT + STRUCTURE_WEIGHT - 1.0) < 1e-9

SOFT_GAP_CREDIT = 0.35

# ------------------------------------------------------------- similarity ----
SEMANTIC_ABS_FLOOR = 0.70
SEMANTIC_ABS_CEILING = 0.88
SEMANTIC_MARGIN_FULL = 0.12      # best - median needed for full credit
SEMANTIC_BASELINE_PCT = 50       # percentile used as the null baseline

SOFT_MATCH_ABS = 0.90            # was 0.86, and measured on padded phrases
SOFT_MATCH_MARGIN = 0.05

# ---------------------------------------------------------- priority depth ---
PRIORITY_FIRST_CREDIT = 0.35     # one line of real evidence
PRIORITY_CREDIT_STEP = 0.325     # per additional distinct evidence line
PRIORITY_FULL_CONTEXTS = 3
PRIORITY_LIST_ONLY_CREDIT = 0.15  # named only in a comma-separated skills dump
STUFFING_RATIO = 3.0

PRIORITY_SKILLS: Dict[str, List[str]] = {
    "JavaScript (ES6+)": [r"javascript", r"es\s?6\+?", r"es20\d{2}", r"\bjs\b"],
    "TypeScript": [r"typescript", r"\bts\b"],
    "React.js": [r"react(?:\.?js)?\b(?!\s*(?:native|query))"],
    "React Native": [r"react\s*native"],
    "Next.js": [r"next\.?\s?js"],
    "Redux Toolkit": [r"redux(?:\s*toolkit)?", r"\brtk\b"],
    "React Query": [r"react\s*query", r"tanstack\s*query"],
    "Zustand": [r"zustand"],
    "Node.js": [r"node\.?\s?js", r"\bnode\b"],
    "GraphQL": [r"graph\s?ql", r"\bapollo\b"],
    "Express.js": [r"express(?:\.?\s?js)?"],
    "SQL": [r"\bsql\b", r"postgres(?:ql)?", r"my\s?sql", r"sqlite",
            r"\bt-sql\b", r"\bpl/?sql\b"],
}

_PRIORITY_PATTERNS: Dict[str, "re.Pattern"] = {
    name: re.compile("|".join(f"(?:{p})" for p in patterns), re.IGNORECASE)
    for name, patterns in PRIORITY_SKILLS.items()
}

# ------------------------------------------------------------------ limits ---
MAX_REQUIREMENTS = 60
MAX_RESUME_UNITS = 250
MIN_UNIT_WORDS = 4
MAX_EMBED_CACHE = 20000

MIN_RESUME_TOKENS = 150
MIN_BULLET_COUNT = 5
SECTION_HEADER_MAX_WORDS = 5

TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9+#]*(?:\.[a-z0-9+#]+)*")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+")
BULLET_PATTERN = re.compile(
    r"^\s*(?:[-*\u2022\u25cf\u25aa\u2023\u00b7\u2043]|\d+[.)])\s+", re.MULTILINE
)

ACTION_VERB = re.compile(
    r"\b(?:built|create[ds]?|design(?:ed)?|develop(?:ed)?|led|manag(?:ed|ing)|"
    r"implement(?:ed)?|improv(?:ed)?|reduc(?:ed)?|increas(?:ed)?|migrat(?:ed)?|"
    r"automat(?:ed)?|shipp(?:ed)?|own(?:ed)?|architect(?:ed)?|optimi[sz](?:ed)?|"
    r"integrat(?:ed)?|deploy(?:ed)?|maintain(?:ed)?|deliver(?:ed)?|launch(?:ed)?|"
    r"refactor(?:ed)?|collaborat(?:ed)?|mentor(?:ed)?|wrote|test(?:ed)?|"
    r"analy[sz](?:ed)?|engineer(?:ed)?|scal(?:ed)?|support(?:ed)?|"
    r"coordinat(?:ed)?|rewrote|rebuilt|debugg(?:ed)?)\b",
    re.IGNORECASE,
)

LIST_SEPARATOR = re.compile(r"[,|/;\u2022]")

BOILERPLATE_MARKERS = (
    "equal opportunity", "we are an", "benefits", "salary", "apply now",
    "about us", "about the company", "our mission", "perks", "eoe",
    "regardless of race", "click here", "job type", "location:",
)

STOPWORDS = {
    "and", "or", "the", "a", "an", "to", "of", "in", "for", "with", "on",
    "at", "by", "from", "as", "is", "are", "be", "will", "you", "we", "our",
    "your", "this", "that", "it", "have", "has", "must", "should", "can",
    "work", "working", "team", "role", "job", "position", "candidate",
    "experience", "years", "year", "strong", "good", "excellent", "ability",
    "responsibilities", "requirements", "preferred", "plus", "etc",
    "company", "opportunity", "environment", "including", "across",
}

_embedder = None
_embed_cache: "OrderedDict[str, np.ndarray]" = OrderedDict()


# ------------------------------------------------------------- embeddings ----
def get_embedder() -> TextEmbedding:
    global _embedder
    if _embedder is None:
        _embedder = TextEmbedding(model_name=SEMANTIC_MODEL_NAME)
    return _embedder


def _embed(phrases: List[str]) -> np.ndarray:
    if not phrases:
        return np.zeros((0, 384), dtype=np.float32)

    fresh = [p for p in dict.fromkeys(phrases) if p not in _embed_cache]
    if fresh:
        vectors = np.array(list(get_embedder().embed(fresh)), dtype=np.float32)
        vectors = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-9)
        for phrase, vector in zip(fresh, vectors):
            _embed_cache[phrase] = vector

        while len(_embed_cache) > MAX_EMBED_CACHE:
            _embed_cache.popitem(last=False)

    for phrase in phrases:
        _embed_cache.move_to_end(phrase)

    return np.vstack([_embed_cache[p] for p in phrases])


def _margin_credit(similarity: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:

    if similarity.size == 0:
        empty = np.zeros(similarity.shape[0], dtype=np.float32)
        return empty, empty, np.zeros(similarity.shape[0], dtype=int)

    best_idx = similarity.argmax(axis=1)
    best_sim = similarity.max(axis=1)

    absolute = (best_sim - SEMANTIC_ABS_FLOOR) / (
        SEMANTIC_ABS_CEILING - SEMANTIC_ABS_FLOOR
    )
    absolute = np.clip(absolute, 0.0, 1.0)

    if similarity.shape[1] < 3:
        # Too few candidates for a meaningful baseline; absolute view only.
        return absolute, best_sim, best_idx

    baseline = np.percentile(similarity, SEMANTIC_BASELINE_PCT, axis=1)
    relative = np.clip((best_sim - baseline) / SEMANTIC_MARGIN_FULL, 0.0, 1.0)

    return np.minimum(absolute, relative), best_sim, best_idx


# ------------------------------------------------------------------ text -----
def _normalize_skill(skill: str) -> str:
    """node.js, Node JS and NodeJS must all resolve to one key."""
    return re.sub(r"[^a-z0-9+#]", "", str(skill).lower().strip())


def _tokenize(text: str) -> List[str]:
    return [t.rstrip(".") for t in TOKEN_PATTERN.findall((text or "").lower())]


def _priority_name(term: str) -> Optional[str]:
    """Which priority skill (if any) a raw term refers to."""
    for name, pattern in _PRIORITY_PATTERNS.items():
        if pattern.search(term or ""):
            return name
    return None


def _is_list_line(line: str) -> bool:

    parts = [p.strip() for p in LIST_SEPARATOR.split(line) if p.strip()]
    if len(parts) < 3:
        return False
    if ACTION_VERB.search(line):
        return False
    return sum(len(p.split()) for p in parts) / len(parts) <= 3.0


def _split_units(text: str, limit: int) -> List[str]:
    units: List[str] = []

    for line in (text or "").splitlines():
        line = re.sub(r"\s+", " ", line).strip(" \t\u2022-*\u25cf")
        if not line:
            continue

        parts = SENTENCE_SPLIT.split(line) if len(line.split()) > 40 else [line]

        for part in parts:
            part = part.strip()
            if len(part.split()) < MIN_UNIT_WORDS:
                continue
            if part.endswith(":"):          # section header, not content
                continue
            units.append(part)

    return units[:limit]


def _split_requirements(job_desc: str) -> List[str]:
    requirements: List[str] = []

    for unit in _split_units(job_desc, MAX_REQUIREMENTS * 3):
        lowered = unit.lower()
        if any(marker in lowered for marker in BOILERPLATE_MARKERS):
            continue
        if not {t for t in _tokenize(unit) if t not in STOPWORDS and len(t) > 1}:
            continue
        requirements.append(unit)

    return requirements[:MAX_REQUIREMENTS]


def getting_keywords(text):

    from services.skill_service import get_keywords
    return get_keywords(text)


# ------------------------------------------------------------- soft gaps -----
def ats_simulation(resume_text: str, job_desc: str) -> Tuple[List[str], List[str]]:
    """
    Split JD keywords the resume is missing into:
      soft_gaps — the resume says the same thing in different words
      hard_gaps — a real skill gap
    """
    resume_words = set(getting_keywords(resume_text or ""))
    job_words = set(getting_keywords(job_desc or ""))
    missing = sorted(job_words - resume_words)

    if not missing or not resume_words:
        return [], missing

    resume_terms = sorted(resume_words)

    resume_vecs = _embed([f"experience with {w}" for w in resume_terms])
    missing_vecs = _embed([f"experience with {t}" for t in missing])

    similarity = missing_vecs @ resume_vecs.T
    best_idx = similarity.argmax(axis=1)
    best_sim = similarity.max(axis=1)

    if similarity.shape[1] >= 3:
        baseline = np.percentile(similarity, SEMANTIC_BASELINE_PCT, axis=1)
    else:
        baseline = np.zeros_like(best_sim)

    soft_gaps: List[str] = []
    hard_gaps: List[str] = []

    for i, term in enumerate(missing):
        match = resume_terms[int(best_idx[i])]

        term_priority = _priority_name(term)
        match_priority = _priority_name(match)
        distinct_skills = (
            term_priority is not None
            and match_priority is not None
            and term_priority != match_priority
        )

        is_soft = (
            not distinct_skills
            and best_sim[i] >= SOFT_MATCH_ABS
            and (best_sim[i] - baseline[i]) >= SOFT_MATCH_MARGIN
        )
        (soft_gaps if is_soft else hard_gaps).append(term)

    return soft_gaps, hard_gaps


# -------------------------------------------------------- priority depth -----
def get_priority_skill_depth(
    resume_text: str, job_desc: str = ""
) -> Tuple[float, List[Dict], List[str]]:

    lines = [line for line in (resume_text or "").splitlines() if line.strip()]
    if not lines:
        return 0.0, [], []

    jd_text = job_desc or ""
    relevant = [
        name for name, pattern in _PRIORITY_PATTERNS.items()
        if pattern.search(jd_text)
    ]
    if not relevant:
        return 0.0, [], []

    line_is_list = [_is_list_line(line) for line in lines]

    detail: List[Dict] = []
    warnings: List[str] = []
    total_credit = 0.0

    for name in relevant:
        pattern = _PRIORITY_PATTERNS[name]

        evidence_contexts = 0
        list_contexts = 0
        occurrences = 0

        for line, is_list in zip(lines, line_is_list):
            hits = len(pattern.findall(line))
            if not hits:
                continue
            occurrences += hits
            if is_list:
                list_contexts += 1
            else:
                evidence_contexts += 1

        if evidence_contexts:
            credit = min(
                1.0,
                PRIORITY_FIRST_CREDIT
                + PRIORITY_CREDIT_STEP * (evidence_contexts - 1),
            )
        elif list_contexts:
            credit = PRIORITY_LIST_ONLY_CREDIT
        else:
            credit = 0.0

        total_credit += credit
        contexts = evidence_contexts + list_contexts

        if contexts and occurrences / contexts >= STUFFING_RATIO:
            warnings.append(
                f"{name} is repeated {occurrences} times in only {contexts} "
                f"line(s); spread it across real achievements instead."
            )
        elif list_contexts and not evidence_contexts:
            warnings.append(
                f"{name} only appears in a skills list. Show it inside a "
                f"bullet that describes what you built with it."
            )

        detail.append({
            "skill": name,
            "contexts": contexts,
            "evidence_contexts": evidence_contexts,
            "list_contexts": list_contexts,
            "occurrences": occurrences,
            "credit": round(credit, 2),
        })

    detail.sort(key=lambda d: (-d["credit"], d["skill"]))

    return total_credit / len(relevant), detail, warnings


# --------------------------------------------------------- skill coverage ----
def _skill_present(skill: str, compact_resume: str) -> bool:
    key = _normalize_skill(skill)
    return bool(key) and key in compact_resume


def get_skill_coverage(
    required_skills: Sequence[str],
    matched_skills: Sequence[str],
    soft_gaps: Sequence[str] = (),
    resume_text: str = "",
) -> float:
 
    required = {_normalize_skill(s) for s in required_skills if str(s).strip()}
    required.discard("")
    if not required:
        return 0.0

    matched = {_normalize_skill(s) for s in matched_skills}
    matched.discard("")

    if resume_text:
        compact = _normalize_skill(resume_text)
        matched = {s for s in matched if _skill_present(s, compact)}

    soft = {_normalize_skill(s) for s in soft_gaps}

    hits = len(required & matched)
    partial = len((required & soft) - matched) * SOFT_GAP_CREDIT

    return min(1.0, (hits + partial) / len(required))


# ------------------------------------------------------ semantic coverage ----
def get_semantic_coverage(
    resume_text: str, job_desc: str
) -> Tuple[float, List[Dict]]:
    requirements = _split_requirements(job_desc)
    resume_units = _split_units(resume_text, MAX_RESUME_UNITS)

    if not requirements or not resume_units:
        return 0.0, []

    req_vecs = _embed(requirements)
    res_vecs = _embed(resume_units)

    similarity = req_vecs @ res_vecs.T
    credit, best_sim, best_idx = _margin_credit(similarity)

    detail = [
        {
            "requirement": requirements[i],
            "best_match": resume_units[int(best_idx[i])],
            "similarity": round(float(best_sim[i]), 3),
            "credit": round(float(credit[i]), 3),
        }
        for i in range(len(requirements))
    ]
    detail.sort(key=lambda d: d["credit"])

    return float(credit.mean()), detail


# -------------------------------------------------------------- structure ----
def get_structure_score(resume_text: str) -> Tuple[float, List[str]]:
    text = resume_text or ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    checks: List[bool] = []
    issues: List[str] = []

    has_email = bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text))
    checks.append(has_email)
    if not has_email:
        issues.append("No email address found.")

    has_phone = bool(re.search(r"(\+?\d[\d\s().-]{7,}\d)", text))
    checks.append(has_phone)
    if not has_phone:
        issues.append("No phone number found.")

    # A section counts only if it appears as a short standalone header line.
    # "experience" occurring somewhere in a sentence proves nothing.
    headers = [
        line.lower().rstrip(":").strip()
        for line in lines
        if len(line.split()) <= SECTION_HEADER_MAX_WORDS
    ]

    for label, markers in (
        ("experience", ("experience", "employment", "work history")),
        ("education", ("education", "academic", "qualification")),
        ("skills", ("skills", "technical skills", "technologies")),
    ):
        found = any(m in header for header in headers for m in markers)
        checks.append(found)
        if not found:
            issues.append(
                f"No clearly labelled {label} section header "
                f"(parsers look for a short line on its own)."
            )

    bullets = len(BULLET_PATTERN.findall(text))
    if bullets < MIN_BULLET_COUNT:
        # Fallback for resumes that use plain lines, but the line still has to
        # read like a duty statement rather than just be a line of some length.
        bullets = sum(
            1 for line in lines
            if 4 <= len(line.split()) <= 30
            and not line.endswith(":")
            and ACTION_VERB.search(line)
        )
    checks.append(bullets >= MIN_BULLET_COUNT)
    if bullets < MIN_BULLET_COUNT:
        issues.append(
            "Few achievement bullets; parsers read bulleted, verb-led duties "
            "more reliably."
        )

    long_enough = len(_tokenize(text)) >= MIN_RESUME_TOKENS
    checks.append(long_enough)
    if not long_enough:
        issues.append("Resume text is very short, which may mean extraction failed.")

    return sum(checks) / len(checks), issues


# ---------------------------------------------------------------- report -----
def get_ats_breakdown(
    resume_text: str,
    job_desc: str,
    required_skills: Sequence[str],
    matched_skills: Sequence[str],
) -> Dict:
    soft_gaps, hard_gaps = ats_simulation(resume_text, job_desc)

    skill = get_skill_coverage(
        required_skills, matched_skills, soft_gaps, resume_text=resume_text
    )
    semantic, semantic_detail = get_semantic_coverage(resume_text, job_desc)
    structure, issues = get_structure_score(resume_text)
    depth, depth_detail, stuffing = get_priority_skill_depth(resume_text, job_desc)

    base = (
        skill * SKILL_WEIGHT
        + semantic * SEMANTIC_WEIGHT
        + structure * STRUCTURE_WEIGHT
    )

    depth_applicable = bool(depth_detail)
    if depth_applicable:
        total = base * BASE_POINTS + depth * PRIORITY_POINTS
    else:
        # Posting names no priority skill — score out of the base alone.
        total = base * 100.0

    total = max(0.0, min(100.0, total))

    return {
        "score": round(total, 2),
        "components": {
            "skill_coverage": round(skill * 100, 2),
            "semantic_coverage": round(semantic * 100, 2),
            "structure": round(structure * 100, 2),
            "priority_depth": round(depth * 100, 2),
        },
        "points": {
            "skill_coverage": round(
                skill * SKILL_WEIGHT * (BASE_POINTS if depth_applicable else 100.0), 2
            ),
            "semantic_coverage": round(
                semantic * SEMANTIC_WEIGHT * (BASE_POINTS if depth_applicable else 100.0), 2
            ),
            "structure": round(
                structure * STRUCTURE_WEIGHT * (BASE_POINTS if depth_applicable else 100.0), 2
            ),
            "priority_depth": round(
                depth * PRIORITY_POINTS if depth_applicable else 0.0, 2
            ),
            "max": 100.0,
        },
        "priority_applicable": depth_applicable,
        "soft_gaps": soft_gaps,
        "hard_gaps": hard_gaps,
        "structure_issues": issues + stuffing,
        "priority_skills": depth_detail,
        "priority_missing": [
            d["skill"] for d in depth_detail if d["contexts"] == 0
        ],
        "priority_shallow": [
            d["skill"] for d in depth_detail
            if 0 < d["evidence_contexts"] < PRIORITY_FULL_CONTEXTS
            or (d["evidence_contexts"] == 0 and d["list_contexts"] > 0)
        ],
        "unmet_requirements": [
            d["requirement"] for d in semantic_detail if d["credit"] < 0.35
        ][:8],
    }