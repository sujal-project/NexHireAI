import re
import math
from collections import Counter
from typing import List, Dict

# Optional advanced NLP
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
except:
    nlp = None

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# -----------------------------
# 🔹 GLOBAL SKILL DATABASE
# -----------------------------
COMMON_SKILLS = [
    "python", "java", "sql", "flask", "django",
    "machine learning", "data science", "html", "css",
    "javascript", "react", "node", "aws", "docker",
    "kubernetes", "git", "api", "pandas", "numpy"
]


# -----------------------------
# 🔹 1. SKILL EXTRACTION
# -----------------------------
def extract_skills(text: str) -> List[str]:
    text = text.lower()

    found_skills = set()

    # Rule-based matching
    for skill in COMMON_SKILLS:
        if skill in text:
            found_skills.add(skill)

    # NLP-based extraction (if spaCy available)
    if nlp:
        doc = nlp(text)
        for chunk in doc.noun_chunks:
            chunk_text = chunk.text.strip().lower()
            if len(chunk_text) < 20:
                found_skills.add(chunk_text)

    return list(found_skills)


# -----------------------------
# 🔹 2. JOB RECOMMENDATION (AI)
# -----------------------------
def match_jobs(user_skills: List[str], job_objs: List) -> List:
    if not job_objs:
        return []

    documents = []
    job_map = []

    user_doc = " ".join(user_skills)
    documents.append(user_doc)

    for job in job_objs:
        job_text = f"{job.title} {job.skills}"
        documents.append(job_text)
        job_map.append(job)

    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform(documents)

    user_vector = vectors[0]
    job_vectors = vectors[1:]

    similarities = cosine_similarity(user_vector, job_vectors).flatten()

    scored_jobs = list(zip(job_map, similarities))
    scored_jobs.sort(key=lambda x: x[1], reverse=True)

    return [job for job, score in scored_jobs]


# -----------------------------
# 🔹 3. RESUME SCORING
# -----------------------------
def score_resume(text: str) -> Dict:
    text = text.lower()

    score = 0
    feedback = []

    # Skill presence
    skills_found = extract_skills(text)
    skill_score = min(len(skills_found) * 5, 40)
    score += skill_score

    if skill_score < 20:
        feedback.append("Add more relevant technical skills.")

    # Experience keywords
    if "experience" in text:
        score += 15
    else:
        feedback.append("Mention your experience clearly.")

    # Projects
    if "project" in text:
        score += 15
    else:
        feedback.append("Add project details.")

    # Education
    if "education" in text:
        score += 10

    # Length check
    word_count = len(text.split())
    if word_count > 300:
        score += 10
    else:
        feedback.append("Resume is too short.")

    score = min(score, 100)

    return {
        "score": score,
        "skills": skills_found,
        "feedback": feedback
    }


# -----------------------------
# 🔹 4. INTERVIEW QUESTIONS
# -----------------------------
QUESTION_BANK = {
    "python": [
        "Explain decorators in Python.",
        "What is the difference between list and tuple?",
    ],
    "sql": [
        "What is a JOIN? Explain types.",
        "Difference between WHERE and HAVING?",
    ],
    "machine learning": [
        "Explain bias vs variance.",
        "What is overfitting?",
    ],
    "flask": [
        "Explain Flask request lifecycle.",
        "What is blueprint in Flask?",
    ],
}


def generate_interview_questions(skills: List[str]) -> List[str]:
    questions = []

    for skill in skills:
        if skill in QUESTION_BANK:
            questions.extend(QUESTION_BANK[skill])

    return questions[:10]


# -----------------------------
# 🔹 5. AI CHATBOT (RULE + CONTEXT)
# -----------------------------
def chatbot_response(user_input: str, user_skills: List[str]) -> str:
    user_input = user_input.lower()

    if "job" in user_input:
        return f"Based on your skills ({', '.join(user_skills)}), you should apply for backend or data roles."

    if "improve resume" in user_input:
        return "Add measurable achievements, projects, and relevant skills."

    if "interview" in user_input:
        return "Focus on core concepts and practice problem-solving."

    return "I can help with jobs, resume, and interview preparation."



#-------------- AI CHATBOT ENGINE CONNECT----------

def ai_chatbot_response(message):
    message = message.lower()

    if "job" in message:
        return "You can explore jobs in the jobs section."
    elif "resume" in message:
        return "Upload your resume to get insights."
    else:
        return "I can help with jobs, resumes, and interviews!"


#-------------- MCQ Generator -----------

def generate_mcq_questions(skills):
    
    mcqs = []

    SAMPLE_MCQS = {
        "python": [
            {
                "question": "What is a decorator in Python?",
                "options": [
                    "A function that modifies another function",
                    "A loop structure",
                    "A variable type",
                    "An error handler"
                ],
                "answer": "A function that modifies another function"
            }
        ],
        "sql": [
            {
                "question": "What does JOIN do?",
                "options": [
                    "Combines rows from tables",
                    "Deletes data",
                    "Updates records",
                    "Creates tables"
                ],
                "answer": "Combines rows from tables"
            }
        ],
        "flask": [
            {
                "question": "What is Flask?",
                "options": [
                    "A Python web framework",
                    "A database",
                    "A frontend library",
                    "An OS"
                ],
                "answer": "A Python web framework"
            }
        ]
    }

    for skill in skills:
        if skill in SAMPLE_MCQS:
            mcqs.extend(SAMPLE_MCQS[skill])

    return mcqs[:5]