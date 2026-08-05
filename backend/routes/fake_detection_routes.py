from flask import Blueprint, request, jsonify

from utils.helpers import extract_text

from services.ml_feature_extractor import extract_features
from services.ml_predict import predict

fake_bp = Blueprint("fake_bp", __name__)


@fake_bp.route("/detect_fake_pdf", methods=["POST"])
def detect_fake_pdf():

    files = request.files.getlist("files")

    results = []

    for file in files:

        text = extract_text(file)
        features = extract_features(text)
        result = predict(features)

        results.append({
            "filename": file.filename,
            "result": result["result"],
            "score": result["score"]
        })

    return jsonify({"results": results})