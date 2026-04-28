import pyodbc
from config import Config

def get_connection():
    try:
        conn = pyodbc.connect(Config.DB_CONNECTION_STRING)
        return conn
    except Exception as e:
        print("DB Connection Error:", e)
        raise Exception("Database connection failed")

