from flask import Blueprint, render_template, request, redirect, current_app, send_from_directory
from flask_login import login_required, current_user
from models.db import get_connection
from werkzeug.utils import secure_filename
from services.ai_engine import generate_mcq_questions
import os
import uuid
import PyPDF2

from services.ai_engine import extract_skills, match_jobs

jobs_bp = Blueprint('jobs', __name__)


class JobObj:
    def __init__(self, row):
        self.id = row[0]
        self.title = row[1]
        self.company = row[2]
        self.skills = row[3]
        self.location = row[5]


# ---------------- JOBS ----------------
@jobs_bp.route('/jobs')
@login_required
def jobs():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM jobs")
    all_jobs = cursor.fetchall()

    cursor.execute("SELECT extracted_skills FROM resumes WHERE user_id=?", (current_user.id,))    
    
    res = cursor.fetchone()

    recommended = []

    if res and res[0]:

        user_skills = [s.strip().lower() for s in res[0].split(",")]

        job_objs = [JobObj(j) for j in all_jobs]

        scored = match_jobs(user_skills, job_objs)

        recommended = scored[:5]

    cursor.execute("SELECT job_id FROM applications WHERE user_id=?", (current_user.id,))
    apps = cursor.fetchall()

    current_user_app_ids = [int(a[0]) for a in apps]

    return render_template(
        "jobs.html",
        all_jobs=all_jobs,
        recommended=recommended,
        current_user_app_ids=current_user_app_ids
    )

#------------- recruiter-dashboard ----------

@jobs_bp.route('/recruiter-dashboard')
@login_required
def recruiter_dashboard():

    if current_user.role != "recruiter":
        return "Unauthorized", 403

    conn = get_connection()
    cursor = conn.cursor()

    # ✅ Get jobs
    cursor.execute("SELECT * FROM jobs WHERE recruiter_id=?", (current_user.id,))
    jobs = cursor.fetchall()

    # ✅ Get application counts in ONE query
    cursor.execute("""
        SELECT job_id, COUNT(*) 
        FROM applications 
        WHERE job_id IN (
            SELECT id FROM jobs WHERE recruiter_id=?
        )
        GROUP BY job_id
    """, (current_user.id,))

    counts = cursor.fetchall()

    # convert to dict {job_id: count}
    count_map = {row[0]: row[1] for row in counts}

    job_titles = []
    job_counts = []

    for job in jobs:
        job_titles.append(job[1])  # title
        job_counts.append(count_map.get(job[0], 0))

    return render_template(
         "recruiter_dashboard.html",
         jobs=jobs,
         job_titles=job_titles or [],
         job_counts=job_counts or []
)

#----------------  ADD JOB-----------------

@jobs_bp.route('/add-job', methods=['GET', 'POST'])
@login_required
def add_job():

    if current_user.role != "recruiter":
        return "Unauthorized", 403

    if request.method == "POST":
        title = request.form['title']
        company = request.form['company']
        skills = request.form['skills']
        location = request.form['location']
        description = request.form['description']

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO jobs (title, company, skills, location, description, recruiter_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, company, skills, location, description, current_user.id))

        conn.commit()

        return redirect('/recruiter-dashboard')

    return render_template("add_job.html")

# ---------------- JOB APPLICANTS ----------------
@jobs_bp.route('/job-applicants/<int:job_id>')
@login_required
def job_applicants(job_id):

    if current_user.role != "recruiter":
        return "Unauthorized", 403

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            users.name, 
            users.email, 
            resumes.file_name
        FROM applications
        JOIN users ON users.id = applications.user_id
        LEFT JOIN resumes ON resumes.user_id = users.id
        WHERE applications.job_id = ?
    """, (job_id,))

    applicants = cursor.fetchall()

    return render_template("applicants.html", applicants=applicants)

# ---------------- APPLY ----------------
@jobs_bp.route('/apply/<int:job_id>')
@login_required
def apply(job_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM applications WHERE user_id=? AND job_id=?",
                   (current_user.id, job_id))

    if cursor.fetchone():
        return "Already applied"

    cursor.execute("""
    INSERT INTO applications (user_id, job_id, status)
    VALUES (?,?,?)
    """, (current_user.id, job_id, "Applied"))

    conn.commit()

    return redirect('/my-applications')


#---------------my_applications------------

@jobs_bp.route('/my-applications')
@login_required
def my_applications():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT jobs.title, jobs.company, applications.status, jobs.location
        FROM applications
        JOIN jobs ON jobs.id = applications.job_id
        WHERE applications.user_id=?
    """, (current_user.id,))

    rows = cursor.fetchall()

    applications = []
    for r in rows:
        applications.append({
            "title": r[0],
            "company": r[1],
            "status": r[2],
            "location": r[3]
        })

    return render_template("my_applications.html", applications=applications)




# ---------------- RESUME UPLOAD ----------------
@jobs_bp.route('/upload-resume', methods=['GET','POST'])
@login_required
def upload_resume():

    if request.method == 'POST':

        file = request.files['resume']

        filename = secure_filename(file.filename)
        unique_name = f"{current_user.id}_{uuid.uuid4().hex}.pdf"

        path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)

        file.save(path)

        text = ""
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""

        skills = extract_skills(text)

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM resumes WHERE user_id=?", (current_user.id,))

        cursor.execute("""
        INSERT INTO resumes (user_id, file_name, extracted_skills, score)
        VALUES (?,?,?,?)
        """, (
            current_user.id,
            unique_name,
            ",".join(skills),
            0
        ))

        conn.commit()

        return f"Skills: {skills}"

    return render_template("upload_resume.html")


# ---------------- RESUME VIEW ----------------
@jobs_bp.route('/resume/<filename>')
@login_required
def view_resume(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


#---------------- jobseeker_dashboard -----------

@jobs_bp.route('/dashboard')
@login_required
def jobseeker_dashboard():

    if current_user.role != "jobseeker":
        return redirect('/jobs')

    return render_template("jobseeker_dashboard.html")




# ---------------- ADMIN ----------------
@jobs_bp.route('/admin')
@login_required
def admin():

    if current_user.role != "recruiter":
        return "Unauthorized", 403

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs")
    jobs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM applications")
    apps = cursor.fetchone()[0]

    return render_template("admin.html", users=users, jobs=jobs, apps=apps)


#----------------- CHATBOT BACKEND ROUTE ----------

@jobs_bp.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json()
    msg = data.get("message")

    reply = ai_chatbot_response(msg)  # from ai_engine

    return {"reply": reply}

#----------- resume score ----------

@jobs_bp.route('/resume-score')
@login_required
def resume_score():
    return "<h2>Resume Score Feature Coming Soon</h2>"

#------------ interview prep ----------


from services.ai_engine import generate_interview_questions

@jobs_bp.route('/interview-prep')
@login_required
def interview_prep():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT extracted_skills FROM resumes WHERE user_id=?", (current_user.id,))
    res = cursor.fetchone()

    if not res or not res[0]:
        return "Upload resume first"

    skills = [s.strip().lower() for s in res[0].split(",")]

    questions = generate_interview_questions(skills)

    return render_template(
        "interview.html",
        questions=[(None, s, q, "medium") for s in skills for q in questions]
    )


#--------------- MCQ Generator -----------

@jobs_bp.route('/mcq', methods=['GET', 'POST'])
@login_required
def mcq():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT extracted_skills FROM resumes WHERE user_id=?", (current_user.id,))
    res = cursor.fetchone()

    if not res or not res[0]:
        return "Upload resume first"

    # convert resume skills → list
    skills = [s.strip().lower() for s in res[0].split(",")]

    questions = generate_mcq_questions(skills)

    if request.method == "POST":

        score = 0
        total = len(questions)

        for i, q in enumerate(questions):
            user_answer = request.form.get(f"q{i}")

            if user_answer == q["answer"]:
                score += 1

        return f"<h2>Your Score: {score}/{total}</h2>"

    return render_template("mcq.html", questions=questions)



