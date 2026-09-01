import os
import sqlite3
from flask import Flask, render_template, jsonify
from supabase import create_client, Client

app = Flask(__name__)

# supabase configuration
SUPABASE_URL = "https://dhrxanvrtjzknafcacpf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRocnhhbnZydGp6a25hZmNhY3BmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjQ4OTU0NzMsImV4cCI6MjA0MDQ3MTQ3M30.XZx3n_Xg8m9zP3V4Q2K-Y_T7b0R1S2W3X4Y5Z6A7B8C"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    supabase = None

def fetch_from_any_table(possible_tables):
    # 1. try searching supabase database across all possible table names
    if supabase:
        for table in possible_tables:
            try:
                res = supabase.table(table).select('*').execute()
                if res.data and len(res.data) > 0:
                    return res.data
            except Exception:
                continue

    # 2. fallback to local sqlite database file
    db_path = os.path.join(os.path.dirname(__file__), 'grader.db')
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            for table in possible_tables:
                try:
                    cursor.execute(f"SELECT * FROM {table}")
                    rows = [dict(row) for row in cursor.fetchall()]
                    if rows and len(rows) > 0:
                        conn.close()
                        return rows
                except Exception:
                    continue
            conn.close()
        except Exception:
            pass

    return []

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

@app.route('/')
@app.route('/student')
def student_portal():
    return render_template('student.html')

@app.route('/teacher')
def teacher_dashboard():
    return render_template('teacher.html')

@app.route('/api/assignments', methods=['GET'])
@app.route('/assignments', methods=['GET'])
def get_assignments():
    # checks every table name your dad or you might have used
    data = fetch_from_any_table(['assignments', 'worksheets', 'problems', 'flash_anzan', 'quizzes'])
    return jsonify(data), 200

@app.route('/api/drafts', methods=['GET'])
@app.route('/drafts', methods=['GET'])
def get_drafts():
    data = fetch_from_any_table(['drafts', 'saved_drafts', 'draft_worksheets'])
    return jsonify(data), 200

@app.route('/api/scores', methods=['GET'])
@app.route('/scores', methods=['GET'])
def get_scores():
    data = fetch_from_any_table(['scores', 'grades', 'results', 'student_scores'])
    return jsonify(data), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)