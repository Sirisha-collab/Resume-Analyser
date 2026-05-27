import re
import PyPDF2

def extract_text(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)

    text = ""

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text

    return text

def clean_lines(text):
    return [
        line.strip()
        for line in text.split("\n")
        if len(line.strip()) > 20
    ]

def similar(a, b):
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()

def normalize_skill(skill):
    skill = skill.lower()
    skill = re.sub(r'[^a-z0-9\s]', '', skill)
    return skill.strip()