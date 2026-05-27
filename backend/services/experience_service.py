import re

def predict_experience_level(resume_text):

    text = resume_text.lower()

    junior_keywords = ['intern', 'junior']
    mid_keywords = ['developer', 'engineer']
    senior_keywords = ['senior', 'lead']

    score = {
        "junior": 0,
        "mid": 0,
        "senior": 0
    }

    for kw in junior_keywords:
        if kw in text:
            score['junior'] += 1

    for kw in mid_keywords:
        if kw in text:
            score['mid'] += 1

    for kw in senior_keywords:
        if kw in text:
            score['senior'] += 1

    experience = max(score, key=score.get)

    years = re.findall(r'(\d+)\+?\s*(years|yrs)', text)

    if years:
        max_years = max([int(y[0]) for y in years])

        if max_years < 2:
            experience = 'junior'
        elif max_years < 5:
            experience = 'mid'
        else:
            experience = 'senior'

    return experience.capitalize()