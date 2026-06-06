from flask import Blueprint, request, jsonify
import traceback

from utils.helpers import extract_text

from services.skill_service import (
    analyze_resume,
    skill_gap,
    generate_suggestions
)

from services.experience_service import (
    predict_experience_level
)

from services.roadmap_service import (
    get_learning_roadmap
)

from services.ats_service import (
    ats_simulation
)

from services.resume_fix_service import (
    resume_fix_ai,
    suggest_action_verbs
)

from services.ml_service import (
    extract_features,
    predict_resume_score
)

from services.job_fit_service import (
    predict_job_fit
)

compare_bp = Blueprint(
    "compare",
    __name__
)


# -----------------------
# Multi Resume Comparison
# -----------------------
@compare_bp.route('/compare', methods=['POST'])
def compare_resumes():

    try:

        files = request.files.getlist('resumes')

        job_desc = request.form['job_description']

        results = []

        for file in files:

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

            learning_roadmap = get_learning_roadmap(
                missing
            )

            ats_feedback = ats_simulation(
                resume_text,
                job_desc
            )

            resume_fixes = resume_fix_ai(
                resume_text
            )

            action_verbs = suggest_action_verbs(
                resume_text
            )

            features = extract_features(
                score,
                matched,
                missing,
                experience_level,
                resume_text
            )

            ml_score, confidence = predict_resume_score(
                features
            )

            job_fit = predict_job_fit(
                score,
                matched,
                missing,
                experience_level,
                resume_text,
                job_desc
            )

            results.append({

                "filename": file.filename,

                "score": score,

                "matched_skills": matched[:10],

                "missing_skills": missing[:10],

                "suggestions": suggestions,

                "experience_level": experience_level,

                "learning_roadmap": learning_roadmap,

                "ats_feedback": ats_feedback,

                "resume_fixes": resume_fixes,
                
                "action_verb_suggestions": action_verbs,

                "ml_score": ml_score,

                "ml_confidence": confidence,

                "job_fit_score": job_fit[
                    "job_fit_score"
                ],

                "selection_probability": job_fit[
                    "selection_probability"
                ],

                "recommendation": job_fit[
                    "recommendation"
                ],

                "semantic_similarity": job_fit[
                    "semantic_similarity"
                ]
            })

        return jsonify({
            "comparison": results
        })

    except Exception as e:

        return jsonify({
        "error": str(e),
        "trace": traceback.format_exc()
        }), 500