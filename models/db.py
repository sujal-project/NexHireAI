import pyodbc
from config import Config

def get_connection():
    try:
        return pyodbc.connect(Config.DB_CONNECTION_STRING)
    except Exception as e:
        print("DB Connection Error:", e)
        return None


#def get_connection():
 #   return pyodbc.connect(Config.DB_CONNECTION_STRING)
