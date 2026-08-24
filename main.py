import os
import sqlite3
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Use writeable /tmp directory on Vercel to prevent file permission crashes
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

# Initialize database schema on startup
init_db()

@app.route('/')
def home():
    return render_template('student.html')

@app.route('/teacher')
def teacher():
    return render_template('teacher.html')

@app.route('/worksheet')
def worksheet():
    return render_template('worksheet.html')

@app.route('/results')
def results():
    return render_template('results.html')

if __name__ == '__main__':
    app.run(debug=True)