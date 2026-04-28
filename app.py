from flask import Flask
from flask_login import LoginManager
import os

from config import Config
from routes.auth import auth_bp, User
from routes.jobs import jobs_bp

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

app.register_blueprint(auth_bp)
app.register_blueprint(jobs_bp)

if __name__ == "__main__":
    app.run(debug=True)