import re

from utils.constants import (
    ACTION_VERBS,
    WEAK_TO_STRONG_VERBS
)

from utils.resume_filters import (
    is_resume_bullet,
    is_garbage_line
)

from utils.helpers import clean_lines

MAX_IMPROVEMENTS = 5
MAX_VERB_SUGGESTIONS = 5

METRIC_PLACEHOLDER = "[add a measurable result: %, time saved, users, or revenue]"

DEFAULT_VERB = "Led"


# -----------------------------
# VERB FORMS
# -----------------------------
def _inflect(verb: str) -> set:
  
    v = verb.lower().strip()
    if not v:
        return set()

    forms = {v, v + "s"}

    if v.endswith("e"):
        forms.add(v + "d")
    elif v.endswith("y") and len(v) > 2 and v[-2] not in "aeiou":
        forms.add(v[:-1] + "ied")
    else:
        forms.add(v + "ed")

    # ship -> shipped, plan -> planned
    if (
        len(v) >= 3
        and v[-1] not in "aeiouwxy"
        and v[-2] in "aeiou"
        and v[-3] not in "aeiou"
    ):
        forms.add(v + v[-1] + "ed")

    return forms


# Rule-based inflection cannot produce build -> built or lead -> led, 
IRREGULAR_PAST = {
    "build": "built", "lead": "led", "write": "wrote", "rewrite": "rewrote",
    "make": "made", "keep": "kept", "send": "sent", "buy": "bought",
    "teach": "taught", "bring": "brought", "hold": "held", "find": "found",
    "grow": "grew", "drive": "drove", "oversee": "oversaw", "begin": "began",
    "choose": "chose", "run": "ran", "win": "won", "speak": "spoke",
    "spend": "spent", "rebuild": "rebuilt", "set": "set", "cut": "cut",
    "put": "put", "meet": "met", "take": "took", "give": "gave",
}

ACTION_VERB_FORMS = {form for verb in ACTION_VERBS for form in _inflect(verb)}
ACTION_VERB_FORMS |= {
    IRREGULAR_PAST[v] for v in (x.lower() for x in ACTION_VERBS) if v in IRREGULAR_PAST
}
ACTION_VERB_FORMS |= set(IRREGULAR_PAST.values())


def _looks_like_verb(word: str) -> bool:
  
    if not word:
        return False
    return word in ACTION_VERB_FORMS or (len(word) > 4 and word.endswith("ed"))


# Vague gerunds worth dropping after the opener is removed:
# "Owned managing the pipeline" reads worse than "Owned the pipeline".
VAGUE_GERUND = re.compile(
    r"^(?:managing|handling|working|assisting|helping|supporting|"
    r"overseeing|doing|performing)\s+(?:on|with|in)?\s*",
    re.IGNORECASE,
)


# -----------------------------
# WEAK OPENERS
# -----------------------------

WEAK_OPENER_PATTERN = re.compile(
    r"^\W*(?:"
    r"responsible\s+for|"
    r"was\s+responsible\s+for|"
    r"worked\s+(?:on|with|in|as)|"
    r"helped\s+(?:to\s+)?(?:with|in)?|"
    r"assisted\s+(?:with|in)?|"
    r"involved\s+in|"
    r"tasked\s+with|"
    r"duties\s+included|"
    r"participated\s+in"
    r")\s+",
    re.IGNORECASE,
)

WEAK_ANYWHERE_PATTERN = re.compile(
    r"\b(?:responsible\s+for|worked\s+on|helped\s+with|involved\s+in|"
    r"tasked\s+with|duties\s+included)\b",
    re.IGNORECASE,
)

PASSIVE_PATTERN = re.compile(
    r"\b(?:was|were|is|are|been|being)\b\s+(?:\w+\s+){0,3}?"
    r"(?:developed|built|designed|implemented|created|managed|maintained|"
    r"delivered|handled|used|utilized|utilised|responsible)\b",
    re.IGNORECASE,
)

URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
DIGIT_PATTERN = re.compile(r"\d")
LEADING_BULLET = re.compile(r"^[\s\-*\u2022\u25cf\u2023\u00b7]+")


# -----------------------------
# VALIDATION
# -----------------------------
def is_valid_resume_line(line: str) -> bool:
   
    line = (line or "").strip()

    if len(line) < 8:
        return False

    stripped = URL_PATTERN.sub("", line).strip()
    if len(stripped) < max(8, len(line) * 0.4):
        return False

    # A row of dashes is a separator, not a bullet.
    if line.count("-") > 5 and len(stripped.split()) < 5:
        return False

    return True


# -----------------------------
# WEAK BULLET DETECTION
# -----------------------------
def is_weak_bullet(line: str) -> bool:

    return bool(WEAK_ANYWHERE_PATTERN.search(line or ""))


# -----------------------------
# WEAK STRUCTURE DETECTION
# -----------------------------
def _first_word(line: str) -> str:
    cleaned = LEADING_BULLET.sub("", (line or "").strip())
    match = re.match(r"[A-Za-z]+", cleaned)
    return match.group(0).lower() if match else ""


def is_weak_structure(line: str) -> bool:
    first_word = _first_word(line)
    if not first_word:
        return False

    if not _looks_like_verb(first_word):
        return True

    return bool(PASSIVE_PATTERN.search(line or ""))


# -----------------------------
# BULLET REWRITER
# -----------------------------
def _strong_verb_for(line: str) -> str:
    """Prefer a replacement mapped to the weak verb actually used."""
    lower = (line or "").lower()

    for weak, strong_options in WEAK_TO_STRONG_VERBS.items():
        if re.search(rf"\b{re.escape(str(weak).lower())}\b", lower):
            if strong_options:
                return str(strong_options[0]).strip().capitalize()

    return DEFAULT_VERB


def rewrite_bullet(line: str) -> dict:

    original = (line or "").strip()
    body = LEADING_BULLET.sub("", original)

    body = WEAK_OPENER_PATTERN.sub("", body)
    body = WEAK_ANYWHERE_PATTERN.sub("", body)

    # Removal leaves dangling connectors and doubled spaces behind.
    body = re.sub(r"^\W*(?:to|for|with|on|in)\b\s+", "", body, flags=re.I)
    body = VAGUE_GERUND.sub("", body)
    body = re.sub(r"\s{2,}", " ", body).strip(" ,;:-")

    if not body:
        return {
            "improved": original,
            "needs_metric": False,
            "reason": "Could not rewrite safely; left unchanged.",
        }

    first_word = _first_word(body)
    if not _looks_like_verb(first_word):
        verb = _strong_verb_for(original)
        body = f"{verb} {body[0].lower() + body[1:] if body else body}"
    else:
        body = body[0].upper() + body[1:]

    needs_metric = not DIGIT_PATTERN.search(body)
    improved = f"{body} {METRIC_PLACEHOLDER}" if needs_metric else body

    return {
        "improved": improved,
        "needs_metric": needs_metric,
        "reason": "Replaced a passive opener with an action verb.",
    }


# -----------------------------
# MAIN FIX ENGINE
# -----------------------------
def resume_fix_ai(resume_text: str) -> list:
    lines = clean_lines(resume_text)

    weak_verb_fixes = []
    structure_fixes = []
    seen = set()

    for line in lines:

        if is_garbage_line(line):
            continue

        if not is_resume_bullet(line):
            continue

        if not is_valid_resume_line(line):
            continue

        key = line.strip().lower()
        if key in seen:
            continue
        seen.add(key)

        if is_weak_bullet(line):
            rewrite = rewrite_bullet(line)
            if rewrite["improved"].strip().lower() != key:
                weak_verb_fixes.append({"original": line, **rewrite})

        elif is_weak_structure(line):
            body = LEADING_BULLET.sub("", line.strip())
            first_word = _first_word(body)

            if PASSIVE_PATTERN.search(line) or _looks_like_verb(first_word):
                
                structure_fixes.append({
                    "original": line,
                    "improved": None,
                    "advice": (
                        "Rewrite in active voice, opening with what you did "
                        "rather than what was done."
                    ),
                    "needs_metric": not DIGIT_PATTERN.search(body),
                    "reason": "Passive phrasing detected.",
                })
                continue

            verb = _strong_verb_for(line)
            needs_metric = not DIGIT_PATTERN.search(body)
            improved = f"{verb} {body[0].lower() + body[1:]}" if body else body
            if needs_metric:
                improved = f"{improved} {METRIC_PLACEHOLDER}"

            structure_fixes.append({
                "original": line,
                "improved": improved,
                "advice": None,
                "needs_metric": needs_metric,
                "reason": "Bullet does not open with an action verb.",
            })

    return (weak_verb_fixes + structure_fixes)[:MAX_IMPROVEMENTS]


# -----------------------------
# ACTION VERB SUGGESTIONS
# -----------------------------
def suggest_action_verbs(resume_text: str) -> list:
    lines = clean_lines(resume_text)
    suggestions = []
    seen = set()

    for line in lines:

        if not is_resume_bullet(line):
            continue

        if not is_valid_resume_line(line):
            continue

        key = line.strip().lower()
        if key in seen:
            continue

        best = None
        for weak in WEAK_TO_STRONG_VERBS:
            match = re.search(rf"\b{re.escape(str(weak).lower())}\b", key)
            if match and (best is None or match.start() < best[1]):
                best = (weak, match.start())

        if not best:
            continue

        seen.add(key)
        weak_found = best[0]

        suggestions.append({
            "line": line,
            "weak_verb": weak_found,
            "suggestions": list(WEAK_TO_STRONG_VERBS[weak_found]),
        })

        if len(suggestions) >= MAX_VERB_SUGGESTIONS:
            break

    return suggestions