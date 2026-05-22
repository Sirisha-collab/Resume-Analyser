import re

from utils.constants import (
    ACTION_VERBS,
    WEAK_TO_STRONG_VERBS
)

from utils.helpers import clean_lines

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

def rewrite_bullet(line):

    cleaned = re.sub(
        r"(responsible |worked |helped |involved in|tasked )",
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

        if is_weak_bullet(line):

            improvements.append({
                "original": line,
                "improved": rewrite_bullet(line)
            })

    return improvements[:5]

def suggest_action_verbs(resume_text):

    lines = clean_lines(resume_text)
    suggestions = []

    for line in lines:

        # ✅ FILTER ADDED HERE (THIS IS WHAT YOU WERE MISSING)
        if not is_valid_resume_line(line):
            continue

        lower_line = line.lower()

        weak_found = None

        for weak in WEAK_TO_STRONG_VERBS.keys():
            if weak in lower_line:
                weak_found = weak
                break

        # smarter suggestions
        if weak_found:
            verbs = WEAK_TO_STRONG_VERBS[weak_found]
        else:
            verbs = ACTION_VERBS[:3]

        suggestions.append({
            "line": line,
            "weak_verb": weak_found if weak_found else "none detected",
            "suggestions": verbs
        })

    return suggestions[:5]