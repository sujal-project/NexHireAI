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

    if res and res[0]:
        user_skills = res[0].split(",")

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
    else:
        user_skills = []
    
    cursor.execute("SELECT job_id FROM applications WHERE user_id=?", (current_user.id,))
    user_apps = cursor.fetchall()

    # convert to simple list
    user_app_ids = [a[0] for a in user_apps]

    return render_template(
    "jobs.html",
    all_jobs=all_jobs,
    recommended=recommended,
    current_user_app_ids=user_app_ids
    )


@jobs_bp.route('/add-job', methods=['GET','POST'])
@login_required
def add_job():

    if current_user.role != "recruiter":
        return "Unauthorized"
    
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

        if not file or file.filename == '':
            return "No file selected"

        if not allowed_file(file.filename):
            return "Only PDF files allowed"

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
# AI JOB RECOMMENDATION
# -----------------------
@jobs_bp.route('/recommended-jobs')
@login_required
def recommended_jobs():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT skills FROM resumes WHERE user_id=?", (current_user.id,))
    res = cursor.fetchone()

    if not res:
        return "Upload resume first"

    if res and res[0]:
        user_skills = res[0].split(",")
    else:
        user_skills = []
    
    cursor.execute("SELECT * FROM jobs")
    rows = cursor.fetchall()

    class JobObj:
        def __init__(self, row):
            self.id = row[0]
            self.title = row[1]
            self.company = row[2]
            self.skills = row[3]
            self.location = row[5]

    jobs = [JobObj(r) for r in rows]

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

    if res and res[0]:
        user_skills = res[0].split(",")
    else:
        user_skills = []

    cursor.execute("SELECT * FROM questions")
    questions = cursor.fetchall()

    filtered = [q for q in questions if q[1] in user_skills]
    
    return render_template("interview.html", questions=filtered)

# -----------------------
# ADMIN DASHBOARD
# -----------------------
@jobs_bp.route('/admin')
@login_required
def admin():

    if current_user.role != "recruiter":
        return "Unauthorized"   

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

    if res and res[0]:
        user_skills = res[0].split(",")
    else:
        user_skills = []

    score = min(len(user_skills) * 15, 100)

    return render_template("resume_score.html", score=score, skills=user_skills)

#---------------------------
#   APPLY TO JOB FEATURE
#---------------------------

@jobs_bp.route('/apply/<int:job_id>')
@login_required
def apply(job_id):

    conn = get_connection()
    cursor = conn.cursor()

    # Get latest resume
    cursor.execute("""
    SELECT id FROM resumes WHERE user_id=?
    """, (current_user.id,))
    resume = cursor.fetchone()

    if not resume:
        return "Upload resume before applying"

    resume_id = resume[0]

    cursor.execute("""
    INSERT INTO applications (user_id, job_id, status, resume_id)
    VALUES (?, ?, ?, ?)
    """, (current_user.id, job_id, "Applied", resume_id))
    

    try:
        conn.commit()
    except:
        conn.rollback()
        return "Application failed"

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

#----------------------------------
#   RECRUITER DASHBOARD ROUTE
#----------------------------------

@jobs_bp.route('/recruiter-dashboard')
@login_required
def recruiter_dashboard():

    if current_user.role != "recruiter":
        return "Unauthorized"

    conn = get_connection()
    cursor = conn.cursor()

    # Get recruiter jobs
    cursor.execute("SELECT * FROM jobs WHERE recruiter_id=?", (current_user.id,))
    jobs = cursor.fetchall()

    return render_template("recruiter_dashboard.html", jobs=jobs)

#----------------------------------
#    VIEW APPLICANTS FOR A JOB
#----------------------------------

@jobs_bp.route('/job-applicants/<int:job_id>')
@login_required
def job_applicants(job_id):

    if current_user.role != "recruiter":
        return "Unauthorized"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT users.name, users.email, resumes.file_path
        FROM applications
        JOIN users ON users.id = applications.user_id
        JOIN resumes ON resumes.id = applications.resume_id
        WHERE applications.job_id=?
    """, (job_id,))

    applicants = cursor.fetchall()

    return render_template("applicants.html", applicants=applicants)
