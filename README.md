**Resume Analyser**

Imagine a career coach reading your resume. It first understands your skills and experience, then compares them with what employers are looking for. Finally, it shows where you stand, points out missing skills, and gives personalized suggestions to improve your resume and career opportunities.

**Key Features**
1. ATS Resume Score
2. ML Resume Scoring
3. Deep Learning Resume Ranking
4. Job Fit Prediction
5. Experience Level Prediction
6. Skill Gap Visualization: bar charts and pie charts
7. Learning Skill Gap Roadmap
8. PDF Report Generation
9. Multi-Resume Comparison (Experimental / In Progress)
10. Resume Chat for resumes- ask questions about resume.

**Backend Setup**

### Run Backend:

```bash
cd backend
python app.py
```

**Frontend Setup**

### Run frontend:

```bash
cd frontend
npm start
```

### Run Playwright:

```bash
npx playwright test --headed --debug	  OR
npx playwright test --browser=firefox --headed
```

**🛠️ Tech Stack**
Backend
Python
FastAPI
REST APIs
Machine Learning
Scikit-learn
BERT
NLP
FAISS Vector Search
SpaCy (NER)
Feature Engineering
Frontend
JavaScript
HTML/CSS
Chart.js
Data Processing
Pandas
NumPy

📊 **Screenshots**

LANDING PAGE
<img width="1892" height="885" alt="Screenshot 2026-10-01 122903" src="https://github.com/user-attachments/assets/efd4bbe8-ce08-4963-b252-f0989b58b414" />

OUTPUT
<img width="1903" height="791" alt="Screenshot 2026-10-01 123440" src="https://github.com/user-attachments/assets/7d0896c7-95bd-4d9f-866d-043c967e0b4f" />

📊 **Future Enhancements**
Real-time recruiter dashboard
Live job API integration
Advanced RAG pipeline
LLM fine-tuning
Resume parsing automation
Cloud deployment on Azure/AWS
Production-grade MLOps pipeline
