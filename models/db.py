import pyodbc
from config import Config

def get_connection():
    return pyodbc.connect(Config.DB_CONNECTION_STRING)
