from flask import Blueprint, request, jsonify

from utils.helpers import extract_text

from services.skill_service import (
    analyze_resume,
    skill_gap,
    generate_suggestions
)

from services.experience_service import (
    predict_experience_level
)

from services.ats_service import ats_simulation

from services.resume_fix_service import (
    resume_fix_ai,
    suggest_action_verbs
)

analyze_bp = Blueprint(
    "analyze",
    __name__
)

@analyze_bp.route("/analyze", methods=["POST"])
def analyze():

    try:

        file = request.files["resume"]

        job_desc = request.form["job_description"]

        resume_text = extract_text(file)

        score = analyze_resume(
            resume_text,
            job_desc
        )

        matched, missing = skill_gap(
            resume_text,
            job_desc
        )

        suggestions = generate_suggestions(
            score,
            missing
        )

        experience_level = predict_experience_level(
            resume_text
        )

        ats_feedback = ats_simulation(
            resume_text,
            job_desc
        )

        return jsonify({
            "score": score,
            "matched_skills": matched,
            "missing_skills": missing,
            "suggestions": suggestions,
            "experience_level": experience_level,
            "ats_feedback": ats_feedback
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500