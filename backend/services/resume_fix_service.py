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


# -----------------------------
# VALIDATION
# -----------------------------
def is_valid_resume_line(line):

    line = line.strip()

    if len(line) < 8:
        return False

    if "http" in line.lower():
        return False

    if "github" in line.lower():
        return False

    if line.count("-") > 5:
        return False

    return True


# -----------------------------
# WEAK BULLET DETECTION
# -----------------------------
def is_weak_bullet(line):

    weak_phrases = [
        "responsible",
        "worked",
        "helped",
        "involved in",
        "tasked"
    ]

    return any(
        p in line.lower()
        for p in weak_phrases
    )


# -----------------------------
# WEAK STRUCTURE DETECTION (NEW)
# -----------------------------
ACTION_VERBS_SET = set(v.lower() for v in ACTION_VERBS)

def is_weak_structure(line):

    line = line.strip()
    lower = line.lower()

    words = lower.split()

    if not words:
        return False

    first_word = words[0]

    if first_word not in ACTION_VERBS_SET:
        return True

    passive_patterns = [
        r"\b(was|were|is|are|been)\b .* (developed|built|designed|implemented|created|managed)",
    ]

    if any(re.search(p, lower) for p in passive_patterns):
        return True

    return False

def rewrite_bullet(line):

    cleaned = re.sub(
        r"\b(responsible|worked|helped|involved in|tasked)\b",
        "",
        line,
        flags=re.I
    ).strip()

    if not any(
        cleaned.lower().startswith(v.lower())
        for v in ACTION_VERBS
    ):
        cleaned = f"{ACTION_VERBS[0]} {cleaned}"

    cleaned += " resulting in a 20% improvement."

    return cleaned

def resume_fix_ai(resume_text):

    lines = clean_lines(resume_text)
    improvements = []

    for line in lines:

        if is_garbage_line(line):
            continue

        if not is_resume_bullet(line):
            continue

        if is_weak_bullet(line):

            improvements.append({
                "original": line,
                "improved": rewrite_bullet(line)
            })

        elif is_weak_structure(line):

            improvements.append({
                "original": line,
                "improved": f"{ACTION_VERBS[0]} {line.strip()} resulting in improved clarity."
            })

    return improvements[:5]

def suggest_action_verbs(resume_text):

    lines = clean_lines(resume_text)
    suggestions = []

    for line in lines:

        if not is_resume_bullet(line):
            continue

        lower_line = line.lower()

        weak_found = None

        for weak in WEAK_TO_STRONG_VERBS:
            if weak in lower_line:
                weak_found = weak
                break

        if not weak_found:
            continue

        suggestions.append({
            "line": line,
            "weak_verb": weak_found,
            "suggestions": WEAK_TO_STRONG_VERBS[weak_found]
        })

    return suggestions[:5]
