from sklearn.feature_extraction.text import TfidfVectorizer

from sklearn.metrics.pairwise import cosine_similarity


# -----------------------
# Job Fit Prediction
# -----------------------
def predict_job_fit(
    score,
    matched,
    missing,
    experience_level,
    resume_text,
    job_desc
):

    # Semantic Similarity
    vectorizer = TfidfVectorizer()

    vectors = vectorizer.fit_transform([
        resume_text,
        job_desc
    ])

    similarity = cosine_similarity(
        vectors[0:1],
        vectors[1:2]
    )[0][0]

    semantic_score = similarity * 100

    # Skill Match Ratio
    total_skills = (
        len(matched) +
        len(missing) +
        1
    )

    skill_ratio = (
        len(matched) / total_skills
    ) * 100

    # Experience Weight
    exp_weights = {
        "Junior": 50,
        "Mid": 75,
        "Senior": 90
    }

    experience_score = exp_weights.get(
        experience_level,
        50
    )

    # Final Weighted Score
    fit_score = (
        score * 0.4 +
        semantic_score * 0.3 +
        skill_ratio * 0.2 +
        experience_score * 0.1
    )

    fit_score = round(
        min(fit_score, 100),
        2
    )

    # Recommendation
    if fit_score >= 80:

        recommendation = "Highly Recommended"

        probability = "High"

    elif fit_score >= 60:

        recommendation = "Moderate Match"

        probability = "Medium"

    else:

        recommendation = "Low Match"

        probability = "Low"

    return {
        "job_fit_score": fit_score,
        "selection_probability": probability,
        "recommendation": recommendation,
        "semantic_similarity": round(
            semantic_score,
            2
        )
    }