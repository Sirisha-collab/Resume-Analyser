import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from utils.constants import TECH_SKILLS, SKILL_SYNONYMS
from utils.helpers import similar

def get_keywords(text):

    text = text.lower()

    found_skills = set()

    for skill in TECH_SKILLS:
        if skill in text:
            found_skills.add(skill)

    words = re.findall(r'\b[a-zA-Z0-9+#.]+\b', text)

    for word in words:

        word = SKILL_SYNONYMS.get(word, word)

        if word in TECH_SKILLS:
            found_skills.add(word)

    return found_skills

def analyze_resume(resume_text, job_desc):

    vectorizer = TfidfVectorizer()

    vectors = vectorizer.fit_transform([
        resume_text,
        job_desc
    ])

    score = cosine_similarity(
        vectors[0:1],
        vectors[1:2]
    )[0][0]

    return round(score * 100, 2)

def skill_gap(resume_text, job_text):

    resume_words = get_keywords(resume_text)
    job_words = get_keywords(job_text)

    matched = []
    missing = []

    for job_skill in job_words:

        found = False

        for resume_skill in resume_words:

            if job_skill == resume_skill:
                matched.append(job_skill)
                found = True
                break

            if similar(job_skill, resume_skill) >= 0.85:
                matched.append(job_skill)
                found = True
                break

        if not found:
            missing.append(job_skill)

    return list(set(matched)), list(set(missing))

def generate_suggestions(score, missing_skills):

    suggestions = []

    if score < 50:
        suggestions.append(
            "Your resume has a low match score."
        )

    if missing_skills:
        suggestions.append(
            f"Add these skills: {', '.join(missing_skills[:5])}"
        )

    return suggestions