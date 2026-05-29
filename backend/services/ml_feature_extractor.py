import re

def extract_features(text):

    text = text.lower()

    features = {}

    # Basic stats
    features["word_count"] = len(text.split())
    features["char_count"] = len(text)

    # Skill signals
    skills = ["python", "java", "c++", "sql", "machine learning", "ai", "data"]
    features["skill_count"] = sum(text.count(skill) for skill in skills)

    # Structure signals
    features["email_present"] = 1 if "@" in text else 0
    features["phone_present"] = 1 if re.search(r"\d{10}", text) else 0

    # Experience signals
    features["year_mentions"] = text.count("year")

    # Section detection (weak heuristic)
    features["has_education"] = 1 if "education" in text else 0
    features["has_experience"] = 1 if "experience" in text else 0

    return features