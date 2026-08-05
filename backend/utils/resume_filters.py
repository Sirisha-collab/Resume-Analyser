import re

# -----------------------
# LINE TYPE DETECTION
# -----------------------
import re
from utils.constants import ACTION_VERBS

def is_resume_bullet(line):

    line = line.strip()

    if not line:
        return False

    lower = line.lower()

    # phone numbers
    if re.search(r'\b\d{10,}\b', line):
        return False

    # email
    if "@" in line:
        return False

    #  links
    if "http" in lower:
        return False

    # headings / profile text
    bad_patterns = [
        "mobile",
        "email",
        "e-mail",
        "objective",
        "career summary",
        "professional summary",
        "profile",
        "about me"
    ]

    if any(p in lower for p in bad_patterns):
        return False

    #  too short
    if len(line) < 12:
        return False

    # starts with bullet symbols
    if line.startswith(("-", "•", "*")):
        return True

    #  starts with action verbs
    first_word = line.split()[0].strip(":-•*").capitalize()

    if first_word in ACTION_VERBS:
        return True

    #  everything else treated as paragraph
    return False


# -----------------------
# GARBAGE FILTER (OPTIONAL)
# -----------------------
def is_garbage_line(line):

    if not line:
        return True

    line_lower = line.lower()

    garbage_patterns = [
        "viewport",
        "px",
        "vw",
        "vh",
        "em",
        "rem",
        "css",
        "style",
        "margin",
        "padding"
    ]

    return any(p in line_lower for p in garbage_patterns)