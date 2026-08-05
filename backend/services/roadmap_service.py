import re
import traceback

from utils.resources import LEARNING_RESOURCES
from utils.mappings import ALIASES, PRETTY_NAMES

MIN_CONTAINMENT_LEN = 4  # "go" must not match "django", "r" must not match "react"


# -----------------------
# Normalization
# -----------------------
def normalize_skill(skill: str) -> str:
    return re.sub(r"[^a-z0-9+#]", "", str(skill).lower().strip())

_RESOURCE_INDEX = {normalize_skill(k): k for k in LEARNING_RESOURCES}

_ALIAS_INDEX = {
    normalize_skill(variant): canonical
    for canonical, variants in ALIASES.items()
    for variant in variants
}


# -----------------------
# Shape tolerance
# -----------------------
def _as_resource(resource) -> dict:
    """A resource may be a dict or, in older entries, a plain string."""
    if isinstance(resource, dict):
        return {
            "name": resource.get("name") or resource.get("title") or "Resource",
            "url": resource.get("url") or resource.get("link") or "",
        }
    return {"name": str(resource), "url": ""}


def _unpack_entry(entry) -> dict:
  
    if isinstance(entry, dict):
        raw_resources = entry.get("resources") or []
        projects = [str(p) for p in (entry.get("projects") or [])]
        tools = [str(t) for t in (entry.get("tools") or [])]
    elif isinstance(entry, (list, tuple)):
        raw_resources, projects, tools = list(entry), [], []
    else:
        raw_resources, projects, tools = [], [], []

    return {
        "resources": [_as_resource(r) for r in raw_resources],
        "projects": projects,
        "tools": tools,
    }


# -----------------------
# Skill Resolution
# -----------------------
def resolve_skill_key(skill: str):
   
    skill_norm = normalize_skill(skill)
    if not skill_norm:
        return None

    if skill_norm in _RESOURCE_INDEX:
        return _RESOURCE_INDEX[skill_norm]

    canonical = _ALIAS_INDEX.get(skill_norm)
    if canonical:
        canonical_norm = normalize_skill(canonical)
        if canonical_norm in _RESOURCE_INDEX:
            return _RESOURCE_INDEX[canonical_norm]

    if len(skill_norm) >= MIN_CONTAINMENT_LEN:
        candidates = [
            norm for norm in _RESOURCE_INDEX
            if len(norm) >= MIN_CONTAINMENT_LEN
            and (norm in skill_norm or skill_norm in norm)
        ]
        if candidates:
            return _RESOURCE_INDEX[max(candidates, key=len)]

    return None


# -----------------------
# Learning Roadmap Service
# -----------------------
def get_learning_roadmap(missing_skills: list[str]) -> dict:
    roadmap = {}

    for raw_skill in missing_skills or []:
        try:
            key = resolve_skill_key(raw_skill)
            unpacked = _unpack_entry(LEARNING_RESOURCES.get(key) if key else None)

            display_name = PRETTY_NAMES.get(
                normalize_skill(key) if key else "",
                str(raw_skill).strip().title()
            )

            roadmap[raw_skill] = {
                "display_name": display_name,
                # A gap with no catalog entry is still a gap. Dropping it made
                # the panel report "no gaps to close" while three were listed.
                "has_resources": bool(unpacked["resources"]),
                **unpacked,
            }

        except Exception:
            print(f"ROADMAP FAILED for skill: {raw_skill!r}")
            print(traceback.format_exc())
            roadmap[raw_skill] = {
                "display_name": str(raw_skill).strip().title(),
                "has_resources": False,
                "resources": [],
                "projects": [],
                "tools": [],
            }

    return roadmap