import os
import joblib
import numpy as np

# Get base directory
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Load trained models
rf_model = joblib.load(os.path.join(BASE_DIR, "random_forest.pkl"))
xgb_model = joblib.load(os.path.join(BASE_DIR, "xgboost.pkl"))


def predict(features):

    # Convert features into model input format
    X = np.array([
        features["word_count"],
        features["char_count"],
        features["skill_count"],
        features["email_present"],
        features["phone_present"],
        features["year_mentions"],
        features["has_education"],
        features["has_experience"]
    ]).reshape(1, -1)

    # Predictions (probability of "fake" class)
    rf_prob = rf_model.predict_proba(X)[0][1]
    xgb_prob = xgb_model.predict_proba(X)[0][1]

    # Average ensemble score
    score = (rf_prob + xgb_prob) / 2

    return {
        "result": "Fake Resume" if score > 0.6 else "Genuine Resume",
        "score": float(score)
    }