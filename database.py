import os
import sqlite3

# Check if running in Vercel serverless environment
if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/grader.db"
else:
    DB_PATH = "grader.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn