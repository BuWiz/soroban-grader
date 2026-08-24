import os
import sqlite3
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Use /tmp directory on Vercel to avoid read-only file system errors
DB_PATH = '/tmp/grader.db' if os.environ.get('VERCEL') else 'grader.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT,
            score TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Initialize DB safely on app startup
init_db()

@app.route('/')
def home():
    # If using index.html in a templates folder:
    try:
        return render_template('index.html')
    except Exception:
        return "<h1>Soroban Grader Server is Live!</h1>"

if __name__ == '__main__':
    app.run(debug=True)