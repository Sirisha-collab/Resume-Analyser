import re
from utils.resources import LEARNING_RESOURCES
from utils.mappings import ALIASES, PRETTY_NAMES


# -----------------------
# Normalization
# -----------------------
def normalize_skill(skill: str) -> str:
    """Normalize skill string for consistent matching."""
    skill = skill.lower()
    skill = re.sub(r"[^a-z0-9\s]", "", skill)
    return skill.strip()


# -----------------------
# Skill Resolution
# -----------------------
def resolve_skill_key(skill: str):
    """
    Resolve a raw skill into a canonical key using:
    1. Exact match
    2. Partial match
    3. Alias match
    """

    skill_norm = normalize_skill(skill)

    # 1. Exact + partial match against resource keys
    for key in LEARNING_RESOURCES.keys():
        if key == skill_norm:
            return key
        if key in skill_norm or skill_norm in key:
            return key

    # 2. Alias match
    for canonical, variants in ALIASES.items():
        if skill_norm in variants:
            return canonical

    return None


# -----------------------
# Learning Roadmap Service
# -----------------------
def get_learning_roadmap(missing_skills: list[str]) -> dict:
    """
    Build a structured learning roadmap for missing skills.
    """

    roadmap = {}

    for raw_skill in missing_skills:

        key = resolve_skill_key(raw_skill)
        lookup_key = key or normalize_skill(raw_skill)

        resources = LEARNING_RESOURCES.get(lookup_key)
        if not resources:
            continue

        display_name = PRETTY_NAMES.get(
            lookup_key,
            raw_skill.strip().title()
        )

        roadmap[raw_skill] = {
            "display_name": display_name,
            "resources": [
                {
                    "name": resource["name"],
                    "url": resource["url"]
                }
                for resource in resources
            ]
        }

    return roadmap