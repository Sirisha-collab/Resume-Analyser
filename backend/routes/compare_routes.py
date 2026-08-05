from flask import Blueprint, request, jsonify
import traceback

import uuid

from services.rag_service import create_resume_index
from services.rag_service import answer_question

from utils.helpers import extract_text

from services.skill_service import (
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
    get_ats_breakdown
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

ALLOWED_EXTENSIONS = (".pdf", ".doc", ".docx")
MIN_EXTRACTED_CHARS = 80


### resume search and question answering RAG
@compare_bp.route("/resume-chat", methods=["POST"])
def resume_chat():
    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "Invalid JSON body"}), 400

        resume_id = data.get("resume_id")
        question = data.get("question")

        if not resume_id or not isinstance(resume_id, str):
            return jsonify({"error": "resume_id is required and must be a string"}), 400

        if not question or not isinstance(question, str):
            return jsonify({"error": "question is required and must be a string"}), 400

        result = answer_question(resume_id, question)

        # safety fallback
        if not result or "answer" not in result:
            return jsonify({"answer": "No relevant context found"}), 200

        return jsonify(result), 200

    except Exception:
        # Log the detail; str(e) can carry absolute paths and library
        # internals into the browser.
        print(traceback.format_exc())
        return jsonify({
            "error": "Internal server error"
        }), 500


# ---------------------------------------------------------------- helpers ----
def _base_result(filename):
   
    return {
        "filename": filename,
        "resume_id": None,
        "error": None,
        "warnings": [],

        "score": None,
        "score_breakdown": {},

        "matched_skills": [],
        "missing_skills": [],

        "soft_gaps": [],
        "hard_gaps": [],
        "priority_skills": [],
        "priority_missing": [],
        "priority_shallow": [],
        "unmet_requirements": [],
        "structure_issues": [],
        "ats_feedback": {"soft_gaps": [], "hard_gaps": []},

        "suggestions": [],
        "experience_level": "Unknown",
        "learning_roadmap": [],
        "resume_fixes": [],
        "action_verb_suggestions": [],

        "ml_score": None,
        "ml_confidence": "n/a",
        "job_fit_score": None,
        "selection_probability": "n/a",
        "recommendation": "n/a",
        "semantic_similarity": None,
    }


def _optional(label, filename, warnings, fallback, fn, *args, **kwargs):
    
    try:
        return fn(*args, **kwargs)
    except Exception:
        print(f"{label} FAILED for {filename}")
        print(traceback.format_exc())
        warnings.append(f"{label} could not be generated for this resume.")
        return fallback


def build_failed_result(filename, message):
    result = _base_result(filename)
    result["error"] = message
    result["suggestions"] = [message]
    return result


# --------------------------------------------------------------- analysis ----
def analyze_single_resume(file, job_desc):
    
    filename = file.filename
    result = _base_result(filename)
    warnings = result["warnings"]

    # STEP 1
    resume_text = extract_text(file)

    if not resume_text or len(resume_text) < MIN_EXTRACTED_CHARS:
   
        raise ValueError(
            "Could not read text from this file. "
            "If it is a scanned document, it needs OCR first."
        )

    # STEP 2 - skills first, because the score depends on them
    matched, missing = skill_gap(resume_text, job_desc)

    # skill_gap has already split the posting's skills into found and absent,
    # so their union is the required set the score divides by.
    required_skills = list(matched) + list(missing)

    # STEP 3 - one call; it runs ats_simulation internally
    breakdown = get_ats_breakdown(
        resume_text,
        job_desc,
        required_skills,
        matched
    )

    score = breakdown["score"]

    result.update({
        "score": score,
        "score_breakdown": breakdown["components"],

        # Full lists: the UI charts count these, so truncating to 10 made
        # every well-matched resume look like it matched exactly 10 skills.
        "matched_skills": matched,
        "missing_skills": missing,

        "soft_gaps": breakdown["soft_gaps"],
        "hard_gaps": breakdown["hard_gaps"],
        "priority_skills": breakdown["priority_skills"],
        "priority_missing": breakdown["priority_missing"],
        "priority_shallow": breakdown["priority_shallow"],
        "unmet_requirements": breakdown["unmet_requirements"],
        "structure_issues": breakdown["structure_issues"],

        # Named keys instead of the bare tuple ats_simulation returns.
        "ats_feedback": {
            "soft_gaps": breakdown["soft_gaps"],
            "hard_gaps": breakdown["hard_gaps"],
        },
    })

    # STEP 4
    suggestions = list(generate_suggestions(score, missing))

    for line in breakdown["unmet_requirements"][:3]:
        suggestions.append(f"The posting asks for: {line}")

    if breakdown["priority_shallow"]:
        suggestions.append(
            "Mentioned only once, so add a second concrete use: "
            + ", ".join(breakdown["priority_shallow"][:4])
        )

    suggestions.extend(breakdown["structure_issues"])
    result["suggestions"] = suggestions

    # STEP 5 - feeds the ML features below, so keep a usable default.
    result["experience_level"] = _optional(
        "Experience level", filename, warnings, "Unknown",
        predict_experience_level, resume_text
    )

    # STEP 6 - enrichment. None of this can sink the score above.
    result["learning_roadmap"] = _optional(
        "Learning roadmap", filename, warnings, {},
        get_learning_roadmap, missing
    )

    result["resume_fixes"] = _optional(
        "Resume fixes", filename, warnings, [],
        resume_fix_ai, resume_text
    )

    result["action_verb_suggestions"] = _optional(
        "Action verb suggestions", filename, warnings, [],
        suggest_action_verbs, resume_text
    )

    features = _optional(
        "Feature extraction", filename, warnings, None,
        extract_features,
        score, matched, missing, result["experience_level"], resume_text
    )

    if features is not None:
        ml_score, confidence = _optional(
            "ML resume score", filename, warnings, (None, "n/a"),
            predict_resume_score, features
        )
        result["ml_score"] = ml_score
        result["ml_confidence"] = confidence

    job_fit = _optional(
        "Job fit prediction", filename, warnings, {},
        predict_job_fit,
        score, matched, missing, result["experience_level"], resume_text, job_desc
    )

    result.update({
        "job_fit_score": job_fit.get("job_fit_score"),
        "selection_probability": job_fit.get("selection_probability", "n/a"),
        "recommendation": job_fit.get("recommendation", "n/a"),
        "semantic_similarity": job_fit.get("semantic_similarity"),
    })

    # STEP 7 - indexing is for the chat panel only, so a failure here must
    # not lose the analysis that already succeeded.
    resume_id = str(uuid.uuid4())
    indexed = _optional(
        "Resume indexing", filename, warnings, False,
        lambda: (create_resume_index(resume_id, resume_text), True)[1]
    )
    result["resume_id"] = resume_id if indexed else None

    return result


# -----------------------
# Multi Resume Comparison
# -----------------------
@compare_bp.route('/compare', methods=['POST'])
def compare_resumes():

    files = request.files.getlist('resumes')
    job_desc = (request.form.get('job_description') or "").strip()

    if not files:
        return jsonify({"error": "No resumes uploaded"}), 400

    if not job_desc:
        return jsonify({"error": "job_description is required"}), 400

    results = []

    for file in files:

        if not file or not file.filename:
            continue

        if not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
            results.append(build_failed_result(
                file.filename or "unknown",
                "Unsupported file type. Upload a PDF or Word document."
            ))
            continue

        try:
            results.append(analyze_single_resume(file, job_desc))

        except ValueError as readable_error:
            # Raised deliberately above, so the message is safe to show.
            print("FAILED FILE:", file.filename)
            results.append(build_failed_result(file.filename, str(readable_error)))

        except Exception:
            print("FAILED FILE:", file.filename)
            print(traceback.format_exc())
            results.append(build_failed_result(
                file.filename,
                "This resume could not be analyzed."
            ))

    analyzed = sum(1 for r in results if r["error"] is None)

    return jsonify({
        "comparison": results,
   
        "summary": {
            "total": len(results),
            "analyzed": analyzed,
            "failed": len(results) - analyzed,
        },
    }), 200