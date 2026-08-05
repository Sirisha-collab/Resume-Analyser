from model.experience_model import ExperienceLevelPredictor

_predictor = ExperienceLevelPredictor()

def predict_experience_level(resume_text: str) -> str:
    return _predictor.predict(resume_text)