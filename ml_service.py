import numpy as np

from sklearn.linear_model import LogisticRegression

from services.skill_service import get_keywords


# -----------------------
# Feature Extraction
# -----------------------
def extract_features(
    score,
    matched,
    missing,
    experience_level,
    resume_text
):

    total_skills = len(matched) + len(missing) + 1

    skill_ratio = len(matched) / total_skills

    keyword_density = (
        len(get_keywords(resume_text))
        / (len(resume_text.split()) + 1)
    )

    exp_map = {
        "Fresher": 0,
        "Junior": 1,
        "Mid": 2,
        "Senior": 3
    }

    experience_score = exp_map.get(
        experience_level,
        1
    )

    return [
        score / 100,
        skill_ratio,
        keyword_density,
        experience_score
    ]


# -----------------------
# Train ML Model
# -----------------------
def train_model():

    X = []
    y = []

    # Simulated training data
    for _ in range(200):

        ats = np.random.uniform(0.3, 1.0)

        skill = np.random.uniform(0.2, 1.0)

        keyword = np.random.uniform(0.1, 0.9)

        exp = np.random.randint(0, 4)

        X.append([
            ats,
            skill,
            keyword,
            exp
        ])

        score = (
            ats * 0.4 +
            skill * 0.3 +
            keyword * 0.2 +
            exp * 0.1
        )

        y.append(1 if score > 0.6 else 0)

    model = LogisticRegression()

    model.fit(X, y)

    return model


# -----------------------
# Load Model
# -----------------------
ML_MODEL = train_model()


# -----------------------
# Resume Score Prediction
# -----------------------
def predict_resume_score(features):

    prob = ML_MODEL.predict_proba(
        [features]
    )[0][1]

    score = round(prob * 100, 2)

    if score > 75:
        confidence = "High"

    elif score > 50:
        confidence = "Medium"

    else:
        confidence = "Low"

    return score, confidence