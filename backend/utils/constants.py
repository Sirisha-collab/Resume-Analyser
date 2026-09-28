# -----------------------
# Skill Analysis
# -----------------------
SKILL_SYNONYMS = {
    # AI / data
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "dl": "deep learning",
    "ds": "data science",
    "natural language processing": "nlp",
    "sklearn": "scikit-learn",
    # Languages
    "js": "javascript",
    "py": "python",
    "golang": "go",
    "cpp": "c++",
    "csharp": "c#",
    # Cloud / DevOps
    "amazon web services": "aws",
    "google cloud platform": "gcp",
    "google cloud": "gcp",
    "microsoft azure": "azure",
    "k8s": "kubernetes",
    # Frameworks
    "node.js": "nodejs",
    "node js": "nodejs",
    "react.js": "react",
    "reactjs": "react",
    "vue.js": "vue",
    "vuejs": "vue",
    "angularjs": "angular",
    "express.js": "express",
    "expressjs": "express",
    "springboot": "spring boot",
    "tailwind css": "tailwind",
    "tailwindcss": "tailwind",
    # Databases
    "postgres": "postgresql",
    "mongo": "mongodb",
    # Data / tools / APIs
    "powerbi": "power bi",
    "ms excel": "excel",
    "microsoft excel": "excel",
    "restful api": "rest api",
    "restful apis": "rest api",
    "rest apis": "rest api",
}

TECH_SKILLS = {
    # Languages
    "python", "java", "javascript", "typescript", "c", "c++", "c#", "php",
    "ruby", "go", "swift", "kotlin", "r",

    # Frontend
    "react", "angular", "vue", "html", "css", "bootstrap", "tailwind",

    # Backend
    "nodejs", "express", "django", "flask", ".net", "spring", "spring boot",

    # Databases
    "sql", "mysql", "postgresql", "mongodb", "oracle", "sqlite",

    # Cloud
    "aws", "azure", "gcp", "docker", "kubernetes",

    # AI/ML
    "machine learning", "deep learning", "nlp", "tensorflow",
    "pytorch", "opencv", "artificial intelligence",

    # Data
    "power bi", "tableau", "excel", "pandas", "numpy",

    # Tools
    "git", "github", "jira", "linux", "postman", "figma",

    # APIs
    "rest api", "graphql"
}

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
