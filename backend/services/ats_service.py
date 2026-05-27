import re

from services.skill_service import get_keywords


# -----------------------
# ATS Simulation
# -----------------------
def ats_simulation(resume_text, job_desc):
    feedback = []
    text = resume_text.lower()

    # Check important sections
    if "skills" not in text:
        feedback.append("Missing 'Skills' section.")
    if "experience" not in text:
        feedback.append("Missing 'Experience' section.")
    if "education" not in text:
        feedback.append("Missing 'Education' section.")

    # Check measurable achievements
    if not re.search(r'\d+%', text) and not re.search(r'\d+\s*(years|yrs)', text):
        feedback.append("No measurable achievements found (e.g., %, numbers).")

    # Check formatting issues (basic heuristic)
    if len(re.findall(r'\|', text)) > 5:
        feedback.append("Resume may contain tables or complex formatting.")

    # Keyword match density
    resume_words = set(get_keywords(resume_text))
    job_words = set(get_keywords(job_desc))
    match_ratio = len(resume_words.intersection(job_words)) / (len(job_words) + 1)

    if match_ratio < 0.3:
        feedback.append("Low keyword optimization for ATS.")

    if not feedback:
        feedback.append("Your resume looks ATS-friendly.")

    return feedback
