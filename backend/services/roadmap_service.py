import re

from utils.resources import LEARNING_RESOURCES


# -----------------------
# Normalize Skill
# -----------------------
def normalize_skill(skill):

    skill = skill.lower()

    skill = re.sub(
        r'[^a-z0-9\s]',
        '',
        skill
    )

    return skill.strip()


# -----------------------
# Match Skill to Resource
# -----------------------
def match_skill_to_resource(skill):

    skill_norm = normalize_skill(skill)

    # Exact & Partial Match
    for key in LEARNING_RESOURCES:

        if key == skill_norm:
            return key

        if (
            key in skill_norm or
            skill_norm in key
        ):
            return key

    # Aliases
    aliases = {

    # -------------------
    # DATABASES
    # -------------------
    "sql": ["sql", "database", "db", "query"],
    "mysql": ["mysql", "my sql"],
    "postgresql": ["postgresql", "postgre", "postgres"],
    "mongodb": ["mongodb", "mongo", "nosql"],
    "oracle": ["oracle db", "oracle database"],

    # -------------------
    # PROGRAMMING LANGUAGES
    # -------------------
    "python": ["python", "py"],
    "java": ["java", "core java", "jvm"],
    "javascript": ["javascript", "js", "nodejs", "node.js"],
    "typescript": ["typescript", "ts"],
    "csharp": ["c#", "c sharp", ".net", "dotnet", "asp.net"],
    "cpp": ["c++", "cpp"],
    "go": ["golang", "go"],
    "ruby": ["ruby"],
    "php": ["php"],

    # -------------------
    # FRONTEND
    # -------------------
    "html": ["html", "html5"],
    "css": ["css", "css3", "bootstrap", "tailwind"],
    "react": ["react", "reactjs", "react.js"],
    "angular": ["angular", "angularjs"],
    "vue": ["vue", "vuejs"],

    # -------------------
    # MACHINE LEARNING / AI
    # -------------------
    "machine learning": ["ml", "machine learning", "ai", "artificial intelligence"],
    "deep learning": ["deep learning", "dl", "neural network", "nn"],
    "nlp": ["nlp", "natural language processing"],
    "data science": ["data science", "datascience"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "tensorflow": ["tensorflow", "tf"],
    "pytorch": ["pytorch", "torch"],

    # -------------------
    # CLOUD
    # -------------------
    "aws": ["aws", "amazon web services"],
    "azure": ["azure", "microsoft azure"],
    "gcp": ["gcp", "google cloud", "google cloud platform"],

    # -------------------
    # DEVOPS
    # -------------------
    "docker": ["docker", "containerization"],
    "kubernetes": ["kubernetes", "k8s"],
    "jenkins": ["jenkins", "ci/cd"],
    "git": ["git", "github", "gitlab"],

    # -------------------
    # BIG DATA
    # -------------------
    "hadoop": ["hadoop"],
    "spark": ["spark", "apache spark"],
    "kafka": ["kafka", "apache kafka"],

    # -------------------
    # MOBILE
    # -------------------
    "android": ["android", "android development"],
    "ios": ["ios", "swift ios"],
    "flutter": ["flutter", "dart"],

    # -------------------
    # OTHER COMMON SKILLS
    # -------------------
    "excel": ["excel", "ms excel"],
    "powerbi": ["power bi", "powerbi"],
    "tableau": ["tableau"]
    }

    for key, values in aliases.items():

        if skill_norm in values:
            return key

    return None


# -----------------------
# Learning Roadmap
# -----------------------
def get_learning_links(missing_skills):

    roadmap = {}

    for skill in missing_skills:

        key = match_skill_to_resource(skill)

        if not key:
            key = normalize_skill(skill)

        resources = LEARNING_RESOURCES.get(key)

        if not resources:
            continue

        pretty_names = {

    "sql": "SQL",
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "mongodb": "MongoDB",
    "oracle": "Oracle",

    "python": "Python",
    "java": "Java",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "csharp": "C#",
    "cpp": "C++",

    "react": "React",
    "angular": "Angular",
    "vue": "Vue",

    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "nlp": "NLP",
    "data science": "Data Science",

    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",

    "aws": "AWS",
    "azure": "Azure",
    "gcp": "GCP",

    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "jenkins": "CI/CD",

    "hadoop": "Hadoop",
    "spark": "Spark",

    "git": "Git",
    "excel": "Excel",
    "powerbi": "Power BI",
    "tableau": "Tableau"
    }

        display_name = pretty_names.get(
            key,
            skill.upper()
        )

        roadmap[skill] = {

            "display_name": display_name,

            "resources": [
                {
                    "name": r["name"],
                    "url": r["url"]
                }
                for r in resources
            ]
        }

    return roadmap