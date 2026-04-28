from flask import Blueprint, render_template, request, redirect, current_app, send_from_directory
from flask_login import login_required, current_user
from models.db import get_connection
from werkzeug.utils import secure_filename
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

    cursor.execute("SELECT skills FROM resumes WHERE user_id=?", (current_user.id,))
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
        INSERT INTO resumes (user_id,file_path,extracted_text,skills)
        VALUES (?,?,?,?)
        """, (current_user.id, unique_name, text, ",".join(skills)))

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















