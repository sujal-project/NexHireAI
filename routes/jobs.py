from flask import Blueprint, render_template, request, redirect, current_app
from flask_login import login_required, current_user
from models.db import get_connection
from werkzeug.utils import secure_filename
import os
import PyPDF2

from services.ai_engine import extract_skills, match_jobs

jobs_bp = Blueprint('jobs', __name__)

# -----------------------
# FILE HELPERS
# -----------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def extract_text(path):
    text = ""
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            if page.extract_text():
                text += page.extract_text()
    return text

# -----------------------
# JOB ROUTES
# -----------------------

@jobs_bp.route('/jobs')
@login_required
def jobs():

    conn = get_connection()
    cursor = conn.cursor()

    # -----------------------
    # GET ALL JOBS
    # -----------------------
    cursor.execute("SELECT * FROM jobs")
    all_jobs = cursor.fetchall()

    # -----------------------
    # GET USER SKILLS
    # -----------------------
    cursor.execute("SELECT skills FROM resumes WHERE user_id=?", (current_user.id,))
    res = cursor.fetchone()

    recommended = []

    if res:
        user_skills = res[0].split(",")

        # Convert jobs into simple objects
        class JobObj:
            def __init__(self, row):
                self.id = row[0]
                self.title = row[1]
                self.company = row[2]
                self.skills = row[3]
                self.location = row[5]

        job_objs = [JobObj(j) for j in all_jobs]

        scored = match_jobs(user_skills, job_objs)

        recommended = scored[:5]

    return render_template("jobs.html", all_jobs=all_jobs, recommended=recommended)
# @jobs_bp.route('/jobs')
# @login_required
# def jobs():
#     conn = get_connection()
#     cursor = conn.cursor()
#     cursor.execute("SELECT * FROM jobs")
#     return render_template("jobs.html", jobs=cursor.fetchall())


@jobs_bp.route('/add-job', methods=['GET','POST'])
@login_required
def add_job():
    if request.method == 'POST':
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO jobs (title, company, skills, salary, location, description, recruiter_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            request.form['title'],
            request.form['company'],
            request.form['skills'],
            request.form['salary'],
            request.form['location'],
            request.form['description'],
            current_user.id
        ))

        conn.commit()
        return redirect('/jobs')

    return render_template("add_job.html")

# -----------------------
# RESUME UPLOAD CORRENT
# -----------------------

@jobs_bp.route('/upload-resume', methods=['GET','POST'])
@login_required
def upload_resume():

    if request.method == 'POST':

        file = request.files.get('resume')

        # # ❌ No file
        # if 'resume' not in request.files:
        #     return "No file uploaded"

        # file = request.files['resume']

        # # ❌ Empty filename
        # if file.filename == '':
        #     return "No selected file"

        # # ❌ Invalid type
        # if not allowed_file(file.filename):
        #     return "Only PDF allowed"

        # ✅ SAFE FILE NAME
        filename = secure_filename(file.filename)

        # ✅ PREVENT OVERWRITE (MAIN FIX)
        unique_name = f"{current_user.id}_{filename}"

        path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)

        # ✅ SAVE FILE
        file.save(path)

        # ✅ EXTRACT TEXT
        text = extract_text(path)

        if not text.strip():
            return "Could not extract text from PDF"

        # ✅ EXTRACT SKILLS
        skills = extract_skills(text)

        
        # ✅ SAVE TO DB
        conn = get_connection()
        cursor = conn.cursor()

        # 🔥 DELETE OLD RESUME (ADD HERE)
        cursor.execute("DELETE FROM resumes WHERE user_id=?", (current_user.id,))

        # ✅ INSERT NEW RESUME
        cursor.execute("""
            INSERT INTO resumes (user_id, file_path, extracted_text, skills)
            VALUES (?, ?, ?, ?)
        """, (
            current_user.id,
            path,
            text,
            ",".join(skills)
        ))

        conn.commit()

        return f"Skills extracted: {skills}"

    return render_template("upload_resume.html")

# -----------------------
# RESUME UPLOAD OLD
# -----------------------
# @jobs_bp.route('/upload-resume', methods=['GET','POST'])
# @login_required
# def upload_resume():

#     if request.method == 'POST':

#         if 'resume' not in request.files:
#             return "No file uploaded"

#         file = request.files['resume']

#         if file.filename == '':
#             return "No selected file"

#         if file and allowed_file(file.filename):

#             filename = secure_filename(file.filename)
#             path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

#             file.save(path)

#             text = extract_text(path)
#             skills = extract_skills(text)

#             conn = get_connection()
#             cursor = conn.cursor()

#             cursor.execute("""
#                 INSERT INTO resumes (user_id, file_path, extracted_text, skills)
#                 VALUES (?, ?, ?, ?)
#             """, (current_user.id, path, text, ",".join(skills)))

#             conn.commit()

#             return f"Extracted Skills: {skills}"

#         return "Only PDF allowed"

#     return render_template("upload_resume.html")

# -----------------------
# AI JOB RECOMMENDATION
# -----------------------
# @jobs_bp.route('/recommended-jobs')
@login_required
def recommended_jobs():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT skills FROM resumes WHERE user_id=?", (current_user.id,))
    res = cursor.fetchone()

    if not res:
        return "Upload resume first"

    user_skills = res[0].split(",")

    cursor.execute("SELECT * FROM jobs")
    jobs = cursor.fetchall()

    scored = match_jobs(user_skills, jobs)

    return render_template("recommended.html", jobs=scored[:5])

# -----------------------
# INTERVIEW PREP
# -----------------------
@jobs_bp.route('/interview-prep')
@login_required
def interview():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT skills FROM resumes WHERE user_id=?", (current_user.id,))
    res = cursor.fetchone()

    if not res:
        return "Upload resume first"

    skills = res[0].split(",")

    cursor.execute("SELECT * FROM questions")
    questions = cursor.fetchall()

    filtered = [q for q in questions if q.skill in skills]

    return render_template("interview.html", questions=filtered)

# -----------------------
# ADMIN DASHBOARD
# -----------------------
@jobs_bp.route('/admin')
@login_required
def admin():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs")
    jobs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM applications")
    apps = cursor.fetchone()[0]

    return render_template("admin.html", users=users, jobs=jobs, apps=apps)
    

# -----------------------
# ADD RESUME SCORE FEATURE
# -----------------------

@jobs_bp.route('/resume-score')
@login_required
def resume_score():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT skills FROM resumes WHERE user_id=?", (current_user.id,))
    res = cursor.fetchone()

    if not res:
        return "Upload resume first"

    skills = res[0].split(",")

    score = min(len(skills) * 15, 100)

    return render_template("resume_score.html", score=score, skills=skills)


#---------------------------
#   APPLY TO JOB FEATURE
#---------------------------

@jobs_bp.route('/apply/<int:job_id>')
@login_required
def apply(job_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO applications (user_id, job_id, status)
        VALUES (?, ?, ?)
    """, (current_user.id, job_id, "Applied"))

    conn.commit()

    return redirect('/my-applications')

#--------------------------------
#   "MY APPLICATIONS" 
#--------------------------------

@jobs_bp.route('/my-applications')
@login_required
def my_applications():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT jobs.title, applications.status
        FROM applications
        JOIN jobs ON jobs.id = applications.job_id
        WHERE applications.user_id=?
    """, (current_user.id,))

    data = cursor.fetchall()

    return render_template("applications.html", data=data)
