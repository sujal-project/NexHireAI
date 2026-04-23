import os

class Config:
    SECRET_KEY = "supersecretkey"   # change in production

    # Upload config
    UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max file

    # Allowed file types
    ALLOWED_EXTENSIONS = {"pdf"}

    # Database (ODBC)
    
    DB_CONNECTION_STRING = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost;"
        "DATABASE=NexHireAI;"
        "Trusted_Connection=yes;"
    )
