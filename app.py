from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import PyPDF2
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from difflib import SequenceMatcher
from sklearn.linear_model import LogisticRegression
import numpy as np
import re

app = Flask(__name__)
CORS(app)

# -----------------------
# USER LOGIN (simple demo)
# -----------------------
USERS = {"admin": "password"}

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if username in USERS and USERS[username] == password:
        return jsonify({"message": "Login successful", "user": username})
    return jsonify({"error": "Invalid credentials"}), 401

# -----------------------
# PDF Extraction
# -----------------------
def extract_text(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text

# -----------------------
# Skill Analysis
# -----------------------
SKILL_SYNONYMS = {
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "js": "javascript",
    "py": "python",
    "db": "database",
    "pm": "project management"
}

def get_keywords(text):
    text = text.lower()
    vectorizer = CountVectorizer(ngram_range=(1,2), stop_words='english')
    X = vectorizer.fit_transform([text])
    keywords = set(vectorizer.get_feature_names_out())
    normalized = {SKILL_SYNONYMS.get(k, k) for k in keywords}
    return normalized

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def skill_gap(resume_text, job_text):
    resume_words = get_keywords(resume_text)
    job_words = get_keywords(job_text)

    matched = []
    missing = []

    for skill in job_words:
        found = False
        for r_skill in resume_words:
            if similar(skill, r_skill) >= 0.85:
                matched.append(skill)
                found = True
                break
        if not found:
            missing.append(skill)
    return matched, missing

def generate_suggestions(score, missing_skills):
    suggestions = []
    if score < 50:
        suggestions.append("- Your resume has a low match score. Align it with the job description.")
    if score < 70:
        suggestions.append("- Try adding more relevant keywords from the job description.")
    if missing_skills:
        suggestions.append(f"- Consider adding these important skills: {', '.join(missing_skills[:5])}")
    suggestions.append("- Use action verbs and quantify achievements (e.g., 'Increased efficiency by 20%').")
    suggestions.append("- Keep formatting clean and ATS-friendly (avoid tables and images).")
    return suggestions

def analyze_resume(resume_text, job_desc):
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform([resume_text, job_desc])
    score = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
    return round(score * 100, 2)

# -----------------------
# Experience Level Prediction
# -----------------------
def predict_experience_level(resume_text):
    text = resume_text.lower()
    junior_keywords = ['intern', 'junior', 'entry-level', 'trainee']
    mid_keywords = ['mid-level', 'associate', 'developer', 'engineer']
    senior_keywords = ['senior', 'lead', 'manager', 'principal', 'director']

    score = {"junior": 0, "mid": 0, "senior": 0}
    for kw in junior_keywords:
        if kw in text: score['junior'] += 1
    for kw in mid_keywords:
        if kw in text: score['mid'] += 1
    for kw in senior_keywords:
        if kw in text: score['senior'] += 1

    experience = max(score, key=score.get)
    years = re.findall(r'(\d+)\+?\s*(years|yrs)', text)
    if years:
        max_years = max([int(y[0]) for y in years])
        if max_years < 2: experience = 'junior'
        elif max_years < 5: experience = 'mid'
        else: experience = 'senior'
    return experience.capitalize()

# -----------------------
# ATS Simulation
# -----------------------
def ats_simulation(resume_text, job_desc):
    feedback = []
    text = resume_text.lower()

    # Check important sections
    if "skills" not in text:
        feedback.append("Missing 'Skills' section.")
    if "experience" not in text:
        feedback.append("Missing 'Experience' section.")
    if "education" not in text:
        feedback.append("Missing 'Education' section.")

    # Check measurable achievements
    if not re.search(r'\d+%', text) and not re.search(r'\d+\s*(years|yrs)', text):
        feedback.append("No measurable achievements found (e.g., %, numbers).")

    # Check formatting issues (basic heuristic)
    if len(re.findall(r'\|', text)) > 5:
        feedback.append("Resume may contain tables or complex formatting.")

    # Keyword match density
    resume_words = set(get_keywords(resume_text))
    job_words = set(get_keywords(job_desc))
    match_ratio = len(resume_words.intersection(job_words)) / (len(job_words) + 1)

    if match_ratio < 0.3:
        feedback.append("Low keyword optimization for ATS.")

    if not feedback:
        feedback.append("Your resume looks ATS-friendly.")

    return feedback

# -----------------------
# Resume Fix AI + Action Verb Enhancer
# -----------------------
import re

ACTION_VERBS = [
    "Developed", "Implemented", "Designed", "Led", "Optimized",
    "Improved", "Built", "Automated", "Analyzed", "Delivered"
]

WEAK_TO_STRONG_VERBS = {
    "responsible": ["Led", "Managed", "Oversaw"],
    "worked": ["Developed", "Implemented", "Executed"],
    "helped": ["Assisted", "Supported", "Facilitated"],
    "handled": ["Managed", "Directed", "Executed"],
    "used": ["Utilized", "Applied", "Leveraged"],
    "made": ["Created", "Built", "Developed"]
}


# -----------------------
# Clean Resume Lines
# -----------------------
def clean_lines(text):
    return [
        line.strip()
        for line in text.split('\n')
        if len(line.strip()) > 20 and not line.strip().isupper()
    ]


# -----------------------
# Detect Weak Bullet
# -----------------------
def is_weak_bullet(line):
    weak_phrases = [
        "responsible for",
        "worked on",
        "helped with",
        "involved in",
        "tasked with"
    ]
    return any(p in line.lower() for p in weak_phrases)


# -----------------------
# Rewrite Bullet (Fix AI)
# -----------------------
def rewrite_bullet(line):
    original = line

    # Remove weak phrases
    cleaned = re.sub(
        r"(responsible for|worked on|helped with|involved in|tasked with)",
        "",
        line,
        flags=re.I
    ).strip()

    # Add action verb if missing
    if not any(cleaned.lower().startswith(v.lower()) for v in ACTION_VERBS):
        cleaned = f"{ACTION_VERBS[0]} {cleaned}"

    # Add impact if missing
    if not re.search(r'\d+%|\d+\s*(users|clients|projects)', cleaned):
        cleaned += " resulting in a 20% improvement."

    return original.strip(), cleaned.strip()


# -----------------------
# Resume Fix AI
# -----------------------
def resume_fix_ai(resume_text):
    lines = clean_lines(resume_text)
    improvements = []

    for line in lines:
        if is_weak_bullet(line):
            original, improved = rewrite_bullet(line)

            if original != improved:
                improvements.append({
                    "original": original,
                    "improved": improved
                })

    return improvements[:5]


# -----------------------
# Action Verb Suggestions (NEW FEATURE)
# -----------------------
def suggest_action_verbs(resume_text):
    lines = clean_lines(resume_text)
    suggestions = []

    for line in lines:
        words = line.lower().split()

        for weak, strong_list in WEAK_TO_STRONG_VERBS.items():
            if weak in words:
                suggestions.append({
                    "line": line,
                    "weak_verb": weak,
                    "suggestions": strong_list
                })
                break

    return suggestions[:5]

def extract_features(score, matched, missing, experience_level, resume_text):
    total_skills = len(matched) + len(missing) + 1

    skill_ratio = len(matched) / total_skills
    keyword_density = len(get_keywords(resume_text)) / (len(resume_text.split()) + 1)

    exp_map = {
        "Fresher": 0,
        "Junior": 1,
        "Mid": 2,
        "Senior": 3
    }

    experience_score = exp_map.get(experience_level, 1)

    return [
        score / 100,              # ATS score normalized
        skill_ratio,              # skill match ratio
        keyword_density,          # keyword richness
        experience_score          # experience level
    ]

# -----------------------
# Train ML Model (For scoring)
# -----------------------
def train_model():
    X = []
    y = []

    # Simulated training data
    for i in range(200):
        ats = np.random.uniform(0.3, 1.0)
        skill = np.random.uniform(0.2, 1.0)
        keyword = np.random.uniform(0.1, 0.9)
        exp = np.random.randint(0, 4)

        X.append([ats, skill, keyword, exp])

        # Rule-based label (simulate hiring decision)
        score = (ats * 0.4 + skill * 0.3 + keyword * 0.2 + exp * 0.1)

        y.append(1 if score > 0.6 else 0)

    model = LogisticRegression()
    model.fit(X, y)
    return model


ML_MODEL = train_model()

def predict_resume_score(features):
    prob = ML_MODEL.predict_proba([features])[0][1]
    score = round(prob * 100, 2)

    if score > 75:
        confidence = "High"
    elif score > 50:
        confidence = "Medium"
    else:
        confidence = "Low"

    return score, confidence


# -----------------------
# JOB FIT PREDICTION
# -----------------------
def predict_job_fit(score, matched, missing, experience_level, resume_text, job_desc):

    # Semantic Similarity
    vectorizer = TfidfVectorizer()

    vectors = vectorizer.fit_transform([resume_text, job_desc])

    similarity = cosine_similarity(
        vectors[0:1],
        vectors[1:2]
    )[0][0]

    semantic_score = similarity * 100

    # Skill Match Ratio
    total_skills = len(matched) + len(missing) + 1

    skill_ratio = (len(matched) / total_skills) * 100

    # Experience Weight
    exp_weights = {
        "Junior": 50,
        "Mid": 75,
        "Senior": 90
    }

    experience_score = exp_weights.get(experience_level, 50)

    # Final Weighted Score
    fit_score = (
        score * 0.4 +
        semantic_score * 0.3 +
        skill_ratio * 0.2 +
        experience_score * 0.1
    )

    fit_score = round(min(fit_score, 100), 2)

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
        "semantic_similarity": round(semantic_score, 2)
    }

# -----------------------
# Skill Gap Roadmap (Improved)
# -----------------------
LEARNING_RESOURCES = {
    "python": [
        {"name": "Python for Everybody (Coursera)", "url": "https://www.coursera.org/specializations/python"},
        {"name": "Python Bootcamp (Udemy)", "url": "https://www.udemy.com/course/complete-python-bootcamp/"},
        {"name": "Python Learning Path (Microsoft Learn)", "url": "https://learn.microsoft.com/en-us/training/paths/python-language/"}
    ],
    "machine learning": [
        {"name": "Machine Learning - Andrew Ng (Coursera)", "url": "https://www.coursera.org/learn/machine-learning"},
        {"name": "Machine Learning A-Z (Udemy)", "url": "https://www.udemy.com/course/machinelearning/"},
        {"name": "ML Path (Microsoft Learn)", "url": "https://learn.microsoft.com/en-us/training/paths/build-ai-solutions-with-ml/"}
    ],
    "deep learning": [
        {"name": "Deep Learning Specialization (Coursera)", "url": "https://www.coursera.org/specializations/deep-learning"},
        {"name": "Deep Learning (Udemy)", "url": "https://www.udemy.com/course/deeplearning/"}
    ],
    "javascript": [
        {"name": "JavaScript Course (Udemy)", "url": "https://www.udemy.com/course/the-complete-javascript-course/"},
        {"name": "JavaScript Path (Microsoft Learn)", "url": "https://learn.microsoft.com/en-us/training/paths/javascript-first-steps/"}
    ],
    "react": [
        {"name": "React Course (Udemy)", "url": "https://www.udemy.com/course/react-the-complete-guide/"},
        {"name": "React Docs", "url": "https://react.dev"}
    ],
    "azure": [
        {"name": "Azure Fundamentals (Microsoft Learn)", "url": "https://learn.microsoft.com/en-us/training/paths/azure-fundamentals/"},
        {"name": "Azure Course (Udemy)", "url": "https://www.udemy.com/course/azure-essentials/"}
    ],
    "sql": [
        {"name": "SQL for Data Science (Coursera)", "url": "https://www.coursera.org/learn/sql-for-data-science"},
        {"name": "SQL Bootcamp (Udemy)", "url": "https://www.udemy.com/course/the-complete-sql-bootcamp/"}
    ]
}

def normalize_skill(skill):
    skill = skill.lower()
    skill = re.sub(r'[^a-z0-9\s]', '', skill)  # remove symbols
    return skill.strip()


def match_skill_to_resource(skill):
    skill_norm = normalize_skill(skill)

    for key in LEARNING_RESOURCES:
        # Exact match
        if key == skill_norm:
            return key

        # Partial match (important fix)
        if key in skill_norm or skill_norm in key:
            return key

    return None


def get_learning_links(missing_skills):
    roadmap = {}

    for skill in missing_skills:
        matched_key = match_skill_to_resource(skill)

        if matched_key:
            roadmap[skill] = LEARNING_RESOURCES[matched_key]

    return roadmap

# -----------------------
# Single Resume Analyze
# -----------------------
@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        file = request.files['resume']
        job_desc = request.form['job_description']
        resume_text = extract_text(file)

        score = analyze_resume(resume_text, job_desc)
        matched, missing = skill_gap(resume_text, job_desc)
        suggestions = generate_suggestions(score, missing)
        experience_level = predict_experience_level(resume_text)
        learning_roadmap = get_learning_links(missing)
        ats_feedback = ats_simulation(resume_text, job_desc), #for ATS rejecting feedback
        resume_fixes = resume_fix_ai(resume_text),   #for Resume fix
        action_verbs = suggest_action_verbs(resume_text)    #for Action Verb Recommendation
        features = extract_features(score, matched, missing, experience_level, resume_text) #for ML scoring 
        ml_score, confidence = predict_resume_score(features) #for ML scoring
        job_fit = predict_job_fit(score, matched, missing, experience_level,resume_text,job_desc) #for job fit prediction

        return jsonify({
            "score": score,
            "matched_skills": matched[:10],
            "missing_skills": missing[:10],
            "suggestions": suggestions,
            "experience_level": experience_level,
            "learning_roadmap" : get_learning_links(missing),
            "ats_feedback": ats_feedback,   #for ATS rejecting feedback   
            "resume_fixes": resume_fixes,   #for resume fix
            "action_verbs": action_verbs,   #for Action Verb Recommendation
            "ml_score": ml_score,           #for ML scoring
            "ml_confidence": confidence,     #for ML confidence
            "job_fit_score": job_fit["job_fit_score"],   #for job fit prediction
            "selection_probability": job_fit["selection_probability"],
            "recommendation": job_fit["recommendation"],
            "semantic_similarity": job_fit["semantic_similarity"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------
# Multi-Resume Comparison
# -----------------------
@app.route('/compare', methods=['POST'])
def compare_resumes():
    try:
        files = request.files.getlist('resumes')
        job_desc = request.form['job_description']
        results = []

        for file in files:
            resume_text = extract_text(file)
            score = analyze_resume(resume_text, job_desc)
            matched, missing = skill_gap(resume_text, job_desc)
            suggestions = generate_suggestions(score, missing)
            experience_level = predict_experience_level(resume_text)
            learning_roadmap = get_learning_links(missing)
            ats_feedback = ats_simulation(resume_text, job_desc)
            resume_fixes = resume_fix_ai(resume_text)               #for resume fix 
            action_verbs = suggest_action_verbs(resume_text)        #for Action Verb Recommendation
            features = extract_features(score, matched, missing, experience_level, resume_text)     # for ml scoring
            ml_score, confidence = predict_resume_score(features)   #for ML score
            job_fit = predict_job_fit(score, matched, missing, experience_level,resume_text,job_desc) #for job fit prediction

            results.append({
                "filename": file.filename,
                "score": score,
                "matched_skills": matched[:10],
                "missing_skills": missing[:10],
                "suggestions": suggestions,
                "experience_level": experience_level,
                "learning_roadmap": learning_roadmap,
                "ats_feedback": ats_feedback,   #for ATS rejecting feedback
                "resume_fixes": resume_fixes,    #for resume fix 
                "ml_score": ml_score,           #for ML scoring
                "ml_confidence": confidence,
                "job_fit_score": job_fit["job_fit_score"],    #for job fit prediction
                "selection_probability": job_fit["selection_probability"],
                "recommendation": job_fit["recommendation"],
                "semantic_similarity": job_fit["semantic_similarity"],
            })
        return jsonify({"comparison": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------
# PDF Generation
# -----------------------
def create_pdf(score, matched, missing, suggestions, experience_level, filename="report.pdf"):
    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()
    content = []
    content.append(Paragraph(f"ATS Score: {score}%", styles["Title"]))
    content.append(Paragraph(f"Experience Level: {experience_level}", styles["Heading2"]))
    content.append(Paragraph("Matched Skills:", styles["Heading2"]))
    for m in matched: content.append(Paragraph(m, styles["Normal"]))
    content.append(Paragraph("Missing Skills:", styles["Heading2"]))
    for m in missing: content.append(Paragraph(m, styles["Normal"]))
    content.append(Paragraph("Suggestions:", styles["Heading2"]))
    for s in suggestions: content.append(Paragraph(s, styles["Normal"]))
    doc.build(content)
    return filename

def create_comparison_pdf(results, filename="comparison_report.pdf"):
    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()
    content = []
    for r in results:
        content.append(Paragraph(f"Resume: {r['filename']}", styles["Heading2"]))
        content.append(Paragraph(f"ATS Score: {r['score']}%", styles["Normal"]))
        content.append(Paragraph(f"Experience Level: {r['experience_level']}", styles["Normal"]))
        content.append(Paragraph("Matched Skills:", styles["Normal"]))
        for m in r['matched_skills']: content.append(Paragraph(m, styles["Normal"]))
        content.append(Paragraph("Missing Skills:", styles["Normal"]))
        for m in r['missing_skills']: content.append(Paragraph(m, styles["Normal"]))
        content.append(Paragraph("Suggestions:", styles["Normal"]))
        for s in r['suggestions']: content.append(Paragraph(s, styles["Normal"]))
        content.append(Paragraph("----------------------------------------------------", styles["Normal"]))
    doc.build(content)
    return filename

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    file_path = create_pdf(
        data['score'],
        data['matched_skills'],
        data['missing_skills'],
        data['suggestions'],
        data.get('experience_level', 'N/A')
    )
    return send_file(file_path, as_attachment=True)

@app.route('/download_comparison', methods=['POST'])
def download_comparison():
    data = request.json
    file_path = create_comparison_pdf(data['comparison'])
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)