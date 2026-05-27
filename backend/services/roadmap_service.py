import re

from utils.resources import LEARNING_RESOURCES


# -----------------------
# Normalize Skill
# -----------------------
def normalize_skill(skill):

    skill = skill.lower()

    skill = re.sub(
        r'[^a-z0-9\s]',
        '',
        skill
    )

    return skill.strip()


# -----------------------
# Match Skill to Resource
# -----------------------
def match_skill_to_resource(skill):

    skill_norm = normalize_skill(skill)

    # Exact & Partial Match
    for key in LEARNING_RESOURCES:

        if key == skill_norm:
            return key

        if (
            key in skill_norm or
            skill_norm in key
        ):
            return key

    # Aliases
    aliases = {

        "sql": [
            "sql",
            "mysql",
            "postgresql",
            "database",
            "db"
        ],

        "python": [
            "python",
            "py"
        ],

        "javascript": [
            "javascript",
            "js"
        ],

        "machine learning": [
            "ml",
            "machine learning",
            "ai"
        ],

        "java": [
            "java",
            "core java"
        ],

        "csharp": [
            "c#",
            "c sharp",
            ".net",
            "dotnet"
        ],

        "css": [
            "css",
            "css3"
        ]
    }

    for key, values in aliases.items():

        if skill_norm in values:
            return key

    return None


# -----------------------
# Learning Roadmap
# -----------------------
def get_learning_links(missing_skills):

    roadmap = {}

    for skill in missing_skills:

        key = match_skill_to_resource(skill)

        if not key:
            key = normalize_skill(skill)

        resources = LEARNING_RESOURCES.get(key)

        if not resources:
            continue

        pretty_names = {

            "sql": "SQL",

            "mysql": "MySQL",

            "postgresql": "PostgreSQL",

            "csharp": "C#",

            "javascript": "JavaScript",

            "java": "Java", 
            "azure" : "Azure",
            "c++" : "C++",
            "html" : "HTML",

            "AI" : "ai",
            "ML" : "machine learning",
            "deep learning" : "Deep Learning",
            "Hadoop" : "hadoop",
            "css": "CSS"
        }

        display_name = pretty_names.get(
            key,
            skill.upper()
        )

        roadmap[skill] = {

            "display_name": display_name,

            "resources": [
                {
                    "name": r["name"],
                    "url": r["url"]
                }
                for r in resources
            ]
        }

    return roadmap