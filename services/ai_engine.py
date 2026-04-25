import spacy

nlp = spacy.load("en_core_web_sm")

SKILLS = ["python","sql","flask","machine learning","aws","pandas"]

def extract_skills(text):
    doc = nlp(text.lower())
    return list(set(token.text for token in doc if token.text in SKILLS))


def match_jobs(user_skills, jobs):
    results = []

    for job in jobs:
        job_skills = set(job.skills.lower().split(",")) if job.skills else set()

        score = len(set(user_skills) & job_skills) / max(len(job_skills), 1)

        results.append((job, score))

    return sorted(results, key=lambda x: x[1], reverse=True)

# import spacy

# nlp = spacy.load("en_core_web_sm")

# SKILLS = ["python","sql","flask","machine learning","aws","pandas"]

# def extract_skills(text):
#     doc = nlp(text.lower())
#     return list(set([token.text for token in doc if token.text in SKILLS]))


# def match_jobs(user_skills, jobs):
#     results = []

#     for job in jobs:
#         job_skills = set(job.skills.lower().split(","))
#         score = len(set(user_skills) & job_skills) / max(len(job_skills),1)
#         results.append((job, score))

#     return sorted(results, key=lambda x: x[1], reverse=True)
