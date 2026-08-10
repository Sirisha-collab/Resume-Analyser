from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

EXP_WEIGHTS = {"junior": 50.0, "mid": 75.0, "senior": 90.0}
DEFAULT_EXP_SCORE = 50.0


def _clamp(value, lo=0.0, hi=100.0):
    try:
        return max(lo, min(float(value), hi))
    except (TypeError, ValueError):
        return lo

#TF-IDF cosine overlap, 0-100
def _text_similarity(resume_text, job_desc):

    a = (resume_text or "").strip()
    b = (job_desc or "").strip()
    if not a or not b:
        return None

    try:
        vectors = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        ).fit_transform([a, b])
    except ValueError:          
        return None

    return float(cosine_similarity(vectors[0:1], vectors[1:2])[0][0]) * 100.0


def _skill_ratio(matched, missing):
   
    matched_set = {s.strip().lower() for s in (matched or []) if s and s.strip()}
    missing_set = {s.strip().lower() for s in (missing or []) if s and s.strip()}
    missing_set -= matched_set          # matched wins on overlap

    total = len(matched_set) + len(missing_set)
    if total == 0:
        return None
    return 100.0 * len(matched_set) / total


def predict_job_fit(score, matched, missing, experience_level, resume_text, job_desc):
    keyword_score = _clamp(score)
    similarity_score = _text_similarity(resume_text, job_desc)
    skill_ratio = _skill_ratio(matched, missing)
    experience_score = EXP_WEIGHTS.get(
        str(experience_level or "").strip().lower(), DEFAULT_EXP_SCORE
    )

    # Drop unavailable components and renormalize
    components = [
        (keyword_score, 0.40),
        (similarity_score, 0.30),
        (skill_ratio, 0.20),
        (experience_score, 0.10),
    ]
    usable = [(v, w) for v, w in components if v is not None]
    total_weight = sum(w for _, w in usable)
    fit_score = _clamp(sum(v * w for v, w in usable) / total_weight)

    if fit_score >= 80:
        recommendation, probability = "Highly Recommended", "High"
    elif fit_score >= 60:
        recommendation, probability = "Moderate Match", "Medium"
    else:
        recommendation, probability = "Low Match", "Low"

    return {
        "job_fit_score": round(fit_score, 2),
        "selection_probability": probability,
        "recommendation": recommendation,
        "semantic_similarity": round(similarity_score, 2) if similarity_score is not None else None,
        "skill_match_ratio": round(skill_ratio, 2) if skill_ratio is not None else None,
        "keyword_score": round(keyword_score, 2),
        "experience_score": experience_score,
    }