import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from services.skill_service import get_keywords

RANDOM_SEED = 42
TRAINING_SAMPLES = 2000

# Reference points that map raw signals onto 0-1. Calibrate these against
# your own corpus — they define what "perfect" means for each feature.
ATS_REFERENCE = 60.0        # TF-IDF cosine of 60/100 counts as a full match
DENSITY_REFERENCE = 0.12    # ~12% distinct-skill-tokens is a dense resume
MAX_EXPERIENCE_LEVEL = 3

FEATURE_WEIGHTS = (0.4, 0.3, 0.2, 0.1)   # ats, skill, keyword, experience
DECISION_THRESHOLD = 0.6
LABEL_SHARPNESS = 12.0      # lower = fuzzier boundary = calibrated mid-range

EXP_MAP = {"Fresher": 0, "Junior": 1, "Mid": 2, "Senior": 3}
DEFAULT_EXP_LEVEL = 1


def extract_features(score, matched, missing, experience_level, resume_text):
    resume_text = resume_text or ""

    total_skills = len(matched) + len(missing) + 1
    skill_ratio = len(matched) / total_skills

    word_count = len(resume_text.split()) + 1
    raw_density = len(get_keywords(resume_text)) / word_count

    experience_score = EXP_MAP.get(experience_level, DEFAULT_EXP_LEVEL)

    # Every feature normalized to 0-1 so the declared weights mean what they say
    return [
        min(score / ATS_REFERENCE, 1.0),
        min(skill_ratio, 1.0),
        min(raw_density / DENSITY_REFERENCE, 1.0),
        experience_score / MAX_EXPERIENCE_LEVEL,
    ]


def train_model():
    rng = np.random.default_rng(RANDOM_SEED)   # seeded: same model every worker

    ats = rng.uniform(0.0, 1.0, TRAINING_SAMPLES)
    skill = rng.uniform(0.0, 1.0, TRAINING_SAMPLES)
    keyword = rng.uniform(0.0, 1.0, TRAINING_SAMPLES)
    exp = rng.integers(0, MAX_EXPERIENCE_LEVEL + 1, TRAINING_SAMPLES) / MAX_EXPERIENCE_LEVEL

    X = np.column_stack([ats, skill, keyword, exp])

    w_ats, w_skill, w_keyword, w_exp = FEATURE_WEIGHTS
    score = ats * w_ats + skill * w_skill + keyword * w_keyword + exp * w_exp

    # Soft labels instead of a hard cut — keeps probabilities calibrated
    # so the Medium confidence band is actually reachable.
    prob = 1 / (1 + np.exp(-LABEL_SHARPNESS * (score - DECISION_THRESHOLD)))
    y = (rng.uniform(0.0, 1.0, TRAINING_SAMPLES) < prob).astype(int)

    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=1000, random_state=RANDOM_SEED),
    )
    model.fit(X, y)
    return model


_ml_model = None


def get_model():
    """Lazy singleton — no training work at import time."""
    global _ml_model
    if _ml_model is None:
        _ml_model = train_model()
    return _ml_model


def predict_resume_score(features):
    features = np.clip(np.asarray(features, dtype=float), 0.0, 1.0)

    prob = get_model().predict_proba([features])[0][1]
    score = round(prob * 100, 2)

    if score > 75:
        confidence = "High"
    elif score > 50:
        confidence = "Medium"
    else:
        confidence = "Low"

    return score, confidence