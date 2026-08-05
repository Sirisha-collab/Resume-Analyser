import traceback
import uuid

from flask import Blueprint, request, jsonify

from utils.helpers import extract_text

from services.skill_service import (
    skill_gap,
    generate_suggestions
)

from services.experience_service import (
    predict_experience_level
)

from services.ats_service import get_ats_breakdown

from services.resume_fix_service import (
    suggest_action_verbs
)

from services.rag_service import create_resume_index

analyze_bp = Blueprint(
    "analyze",
    __name__
)

ALLOWED_EXTENSIONS = (".pdf", ".doc", ".docx")
MIN_EXTRACTED_CHARS = 80


@analyze_bp.route("/analyze", methods=["POST"])
def analyze():

    file = request.files.get("resume")
    job_desc = (request.form.get("job_description") or "").strip()

    # Validate before the try block, so client mistakes return 400 rather
    # than being reported as server errors.
    if file is None or not file.filename:
        return jsonify({"error": "No resume file was uploaded."}), 400

    if not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        return jsonify({"error": "Upload a PDF or Word document."}), 400

    if not job_desc:
        return jsonify({"error": "Job description is required."}), 400

    try:

        resume_text = extract_text(file)

        if not resume_text or len(resume_text) < MIN_EXTRACTED_CHARS:
            # A scanned PDF extracts to almost nothing and would otherwise
            # score zero with no explanation.
            return jsonify({
                "error": "Could not read text from this file. "
                         "If it is a scanned document, it needs OCR first."
            }), 422

        matched, missing = skill_gap(
            resume_text,
            job_desc
        )

        # skill_gap already split the posting's skills into found and absent,
        # so their union is the required set the score divides by.
        required_skills = list(matched) + list(missing)

        breakdown = get_ats_breakdown(
            resume_text,
            job_desc,
            required_skills,
            matched
        )

        score = breakdown["score"]

        suggestions = generate_suggestions(
            score,
            missing
        )

        # Requirement-level gaps read better than a bare list of keywords.
        suggestions = list(suggestions) + [
            f"The posting asks for: {line}" for line in breakdown["unmet_requirements"][:3]
        ]

        if breakdown["priority_shallow"]:
            suggestions.append(
                "Mentioned only once, so add a second concrete use: "
                + ", ".join(breakdown["priority_shallow"][:4])
            )

        experience_level = predict_experience_level(
            resume_text
        )

        action_verb_suggestions = suggest_action_verbs(
            resume_text
        )

        # Index for the chat panel. Failure here must not fail the analysis.
        resume_id = uuid.uuid4().hex
        try:
            create_resume_index(resume_id, resume_text)
        except Exception:
            traceback.print_exc()
            resume_id = None

        return jsonify({
            "resume_id": resume_id,
            "filename": file.filename,
            "score": score,
            "score_breakdown": breakdown["components"],
            "matched_skills": matched,
            "missing_skills": missing,
            "soft_gaps": breakdown["soft_gaps"],
            "hard_gaps": breakdown["hard_gaps"],
            "priority_skills": breakdown["priority_skills"],
            "priority_missing": breakdown["priority_missing"],
            "unmet_requirements": breakdown["unmet_requirements"],
            "structure_issues": breakdown["structure_issues"],
            "suggestions": suggestions,
            "experience_level": experience_level,
            "action_verb_suggestions": action_verb_suggestions,
        })

    except Exception:
        traceback.print_exc()
        return jsonify({
            "error": "Analysis failed. Please try again."
        }), 500