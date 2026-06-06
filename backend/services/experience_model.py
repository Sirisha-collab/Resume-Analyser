import re
from typing import Dict, List


class ExperienceLevelPredictor:
    """
    Rule-based resume experience classifier (improved version).
    """

    EXPERIENCE_KEYWORDS: Dict[str, List[str]] = {
        "junior": ["intern", "junior", "trainee", "entry level", "fresher"],
        "mid": ["developer", "engineer", "analyst", "associate"],
        "senior": ["senior", "lead", "architect", "manager", "principal"]
    }

    YEAR_PATTERN = r'(\d+)\+?\s*(?:years of experience|yrs of experience)'

    def __init__(self):
        pass

    def _extract_years_of_experience(self, text: str) -> int:
        matches = re.findall(self.YEAR_PATTERN, text)

        if not matches:
            return 0

        years = [int(y) for y in matches]

        # safety filter
        years = [y for y in years if 0 <= y <= 40]

        return max(years) if years else 0

    def _calculate_keyword_scores(self, text: str) -> Dict[str, int]:
        scores = {"junior": 0, "mid": 0, "senior": 0}

        for level, keywords in self.EXPERIENCE_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    if level == "junior":
                        scores[level] += 1
                    elif level == "mid":
                        scores[level] += 2
                    elif level == "senior":
                        scores[level] += 3

        return scores

    def predict(self, resume_text: str) -> str:

        # ✅ validation
        if not resume_text or not isinstance(resume_text, str):
            raise ValueError("resume_text must be a non-empty string")

        text = resume_text.lower().strip()

        # Step 1: keyword scoring
        scores = self._calculate_keyword_scores(text)
        keyword_prediction = max(scores, key=scores.get)

        # Step 2: extract years
        years = self._extract_years_of_experience(text)

        # 🔥 DEBUG (keep temporarily)
        print("===== DEBUG EXPERIENCE =====")
        print("TEXT:", text)
        print("KEYWORD SCORES:", scores)
        print("KEYWORD PREDICTION:", keyword_prediction)
        print("YEARS EXTRACTED:", years)
        print("============================")

        # Step 3: decision logic (years has priority)
        if years > 0:
            if years < 2:
                return "Junior"
            elif years < 5:
                return "Mid"
            else:
                return "Senior"

        # fallback
        return keyword_prediction.capitalize()