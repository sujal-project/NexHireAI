from flask import Blueprint, render_template, request, redirect
from flask_login import UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models.db import get_connection

auth_bp = Blueprint('auth', __name__)

class User(UserMixin):
    def __init__(self, user):
        self.id = user[0]
        self.name = user[1]
        self.email = user[2]
        self.role = user[4]

    @staticmethod
    def get(user_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
        user = cursor.fetchone()
        return User(user) if user else None


@auth_bp.route('/')
def home():
    return render_template("index.html")


@auth_bp.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        conn = get_connection()
        cursor = conn.cursor()

        password = generate_password_hash(request.form['password'])

        cursor.execute("""
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, ?)
        """, (
            request.form['name'],
            request.form['email'],
            password,
            request.form['role']
        ))

        conn.commit()
        return redirect('/login')

    return render_template("register.html")


@auth_bp.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email=?", (request.form['email'],))
        user = cursor.fetchone()

        if user and check_password_hash(user[3], request.form['password']):
            login_user(User(user))
            return redirect('/dashboard')

    return render_template("login.html")


@auth_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == "recruiter":
        return redirect('/jobs')
    return redirect('/recommended-jobs')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')
