import logging
import re
from datetime import date
from typing import Dict, List, Optional, Pattern, Tuple, Union

logger = logging.getLogger(__name__)


class ExperienceLevelPredictor:

    EXPERIENCE_KEYWORDS: Dict[str, List[str]] = {
        "junior": ["intern", "internship", "junior", "trainee", "entry level",
                   "fresher", "graduate", "apprentice"],
        "mid": ["developer", "engineer", "analyst", "associate", "consultant",
                "specialist"],
        "senior": ["senior", "sr", "lead", "architect", "manager", "principal",
                   "head of", "director", "staff engineer"]
    }

    KEYWORD_WEIGHTS: Dict[str, int] = {"junior": 1, "mid": 2, "senior": 3}

    LEVEL_ORDER: List[str] = ["junior", "mid", "senior"]

    DEFAULT_LEVEL = "junior"

    # cap repeated hits so a long resume saying "developer" 10 times
    # doesn't outweigh one "senior" title
    MAX_KEYWORD_HITS = 3

    JUNIOR_MAX_YEARS = 2
    MID_MAX_YEARS = 5
    MAX_YEARS = 40

    # when years sit this close to a threshold, keywords may tip the decision
    BOUNDARY_MARGIN = 0.5

    # "5 years of experience", "5+ yrs exp", "2.5 years' professional experience"
    YEAR_PATTERN = (
        r"(\d{1,2}(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)['’]?\.?\s*"
        r"(?:of\s+)?(?:\w+\s+)?(?:experience|exp)\b"
    )

    # "6 months of experience", "3 months internship"
    MONTH_PATTERN = (
        r"(\d{1,2})\s*\+?\s*(?:months?|mos?)\.?\s*"
        r"(?:of\s+)?(?:\w+\s+)?(?:experience|exp|internship)\b"
    )

    # "2019 - 2022", "Jan 2019 – Present", "03/2020 to date"
    DATE_RANGE_PATTERN = (
        r"(?:\d{1,2}/|[a-z]{3,9}\.?\s+)?((?:19|20)\d{2})\s*(?:-|–|—|to|till)\s*"
        r"(?:\d{1,2}/|[a-z]{3,9}\.?\s+)?"
        r"((?:19|20)\d{2}|present|current|now|today|till date|date)\b"
    )

    PRESENT_WORDS = {"present", "current", "now", "today", "till date", "date"}

    EXPERIENCE_HEADERS = {"experience", "work experience", "professional experience",
                          "employment history", "work history", "employment"}

    OTHER_HEADERS = {"education", "skills", "technical skills", "projects",
                     "certifications", "achievements", "summary", "objective",
                     "awards", "publications", "interests", "hobbies", "languages"}

    EDUCATION_KEYWORDS = ["b.tech", "m.tech", "bachelor", "master", "university",
                          "college", "school", "degree", "mba", "phd", "cgpa", "gpa"]

    def __init__(self, current_year: Optional[int] = None):
        self.current_year = current_year or date.today().year

        self._year_regex: Pattern = re.compile(self.YEAR_PATTERN)
        self._month_regex: Pattern = re.compile(self.MONTH_PATTERN)
        self._date_range_regex: Pattern = re.compile(self.DATE_RANGE_PATTERN)

        # word-boundary patterns so "intern" doesn't match "internal"
        # and "lead" doesn't match "leading"
        self._keyword_patterns: Dict[str, List[Pattern]] = {
            level: [self._build_keyword_pattern(kw) for kw in keywords]
            for level, keywords in self.EXPERIENCE_KEYWORDS.items()
        }

    @staticmethod
    def _build_keyword_pattern(keyword: str) -> Pattern:
        # "entry level" also matches "entry-level"
        escaped = re.escape(keyword).replace(r"\ ", r"[\s-]+")
        return re.compile(r"\b" + escaped + r"\b")

    def _extract_years_of_experience(self, text: str) -> float:
        years = [float(y) for y in self._year_regex.findall(text)]
        months = [float(m) / 12 for m in self._month_regex.findall(text)]

        # safety filter
        values = [v for v in years + months if 0 < v <= self.MAX_YEARS]

        return round(max(values), 1) if values else 0.0

    def _extract_experience_section(self, text: str) -> str:
        section: List[str] = []
        collecting = False

        for line in text.splitlines():
            header = line.strip().rstrip(":").strip()

            if header in self.EXPERIENCE_HEADERS:
                collecting = True
                continue
            if header in self.OTHER_HEADERS:
                collecting = False
                continue
            if collecting:
                section.append(line)

        return "\n".join(section)

    def _extract_years_from_date_ranges(self, text: str) -> float:
        section = self._extract_experience_section(text)

        if section:
            lines = section.splitlines()
        else:
            # no clear section headers: skip lines that look like education
            lines = [line for line in text.splitlines()
                     if not any(kw in line for kw in self.EDUCATION_KEYWORDS)]

        intervals: List[Tuple[int, int]] = []

        for line in lines:
            for start, end in self._date_range_regex.findall(line):
                start_year = int(start)
                end_year = self.current_year if end in self.PRESENT_WORDS else int(end)

                if (self.current_year - self.MAX_YEARS <= start_year
                        <= end_year <= self.current_year):
                    intervals.append((start_year, end_year))

        return float(self._merge_intervals_length(intervals))

    @staticmethod
    def _merge_intervals_length(intervals: List[Tuple[int, int]]) -> int:
        # merge overlapping jobs so parallel roles aren't double counted
        if not intervals:
            return 0

        intervals = sorted(intervals)
        total = 0
        current_start, current_end = intervals[0]

        for start, end in intervals[1:]:
            if start <= current_end:
                current_end = max(current_end, end)
            else:
                total += current_end - current_start
                current_start, current_end = start, end

        total += current_end - current_start
        return total

    def _calculate_keyword_scores(self, text: str) -> Dict[str, int]:
        scores = {level: 0 for level in self.EXPERIENCE_KEYWORDS}

        for level, patterns in self._keyword_patterns.items():
            weight = self.KEYWORD_WEIGHTS[level]
            for pattern in patterns:
                hits = len(pattern.findall(text))
                scores[level] += weight * min(hits, self.MAX_KEYWORD_HITS)

        return scores

    def _get_keyword_prediction(self, scores: Dict[str, int]) -> str:
        if not any(scores.values()):
            return self.DEFAULT_LEVEL

        best = max(scores.values())

        # ties go to the more senior level
        for level in reversed(self.LEVEL_ORDER):
            if scores[level] == best:
                return level

        return self.DEFAULT_LEVEL

    def _level_from_years(self, years: float) -> str:
        if years < self.JUNIOR_MAX_YEARS:
            return "junior"
        elif years < self.MID_MAX_YEARS:
            return "mid"
        return "senior"

    def _is_near_boundary(self, years: float, level_a: str, level_b: str) -> bool:
        index_a = self.LEVEL_ORDER.index(level_a)
        index_b = self.LEVEL_ORDER.index(level_b)

        if abs(index_a - index_b) != 1:
            return False

        thresholds = [self.JUNIOR_MAX_YEARS, self.MID_MAX_YEARS]
        boundary = thresholds[min(index_a, index_b)]

        return abs(years - boundary) <= self.BOUNDARY_MARGIN

    def predict_with_details(self, resume_text: str) -> Dict[str, Union[str, float, Dict[str, int]]]:
        if not isinstance(resume_text, str) or not resume_text.strip():
            raise ValueError("resume_text must be a non-empty string")

        text = resume_text.lower().strip()

        # Step 1: keyword scoring
        scores = self._calculate_keyword_scores(text)
        keyword_prediction = self._get_keyword_prediction(scores)

        # Step 2: extract years (explicit statement first, then date ranges)
        years = self._extract_years_of_experience(text)
        source = "explicit_years"

        if years == 0:
            years = self._extract_years_from_date_ranges(text)
            source = "date_ranges"

        # Step 3: decision logic (years has priority)
        if years > 0:
            level = self._level_from_years(years)
            confidence = 0.9 if source == "explicit_years" else 0.75

            if level == keyword_prediction:
                confidence += 0.05
            elif any(scores.values()) and self._is_near_boundary(years, level, keyword_prediction):
                # borderline years: let a strong title signal tip it
                level = keyword_prediction
                source += "+keywords"
                confidence -= 0.15
        else:
            # fallback
            level = keyword_prediction
            source = "keywords"
            total = sum(scores.values())
            confidence = round(0.6 * scores[level] / total, 2) if total else 0.2

        result = {
            "level": level.capitalize(),
            "years": years,
            "source": source,
            "confidence": round(min(confidence, 1.0), 2),
            "keyword_scores": scores,
            "keyword_prediction": keyword_prediction,
        }

        logger.debug("Experience prediction: %s", result)

        return result

    def predict(self, resume_text: str) -> str:
        return self.predict_with_details(resume_text)["level"]

    def predict_batch(self, resume_texts: List[str]) -> List[str]:
        return [self.predict(text) for text in resume_texts]


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    predictor = ExperienceLevelPredictor()

    samples = [
        "Software Engineer with 6+ years of experience in backend systems.",
        "Fresher looking for an entry-level role. 6 months internship at XYZ.",
        "Experience\nSenior Developer, Acme  Jan 2019 - Present\n"
        "Developer, Foo  2016 - 2019\nEducation\nB.Tech, ABC University 2012 - 2016",
        "Worked on internal tools, leading small features as a developer.",
    ]

    for sample in samples:
        print(predictor.predict(sample), "|", predictor.predict_with_details(sample)["source"])
