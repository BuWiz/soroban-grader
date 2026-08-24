import os
import sqlite3
from flask import Flask

base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, 'templates')

app = Flask(__name__, template_folder=template_dir)

# Set DB path to Vercel's writable /tmp directory in production
if os.environ.get('VERCEL'):
    DB_PATH = '/tmp/soroban.db'
else:
    DB_PATH = os.path.join(base_dir, 'soroban.db')

def init_db():
    """Automatically create tables in /tmp if they don't exist yet"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Replace these table creation queries with your actual schema if different
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT,
            score TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Always ensure database schema exists before handling requests
init_db()