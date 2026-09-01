import os
from flask import Flask, render_template, jsonify
from supabase import create_client, Client

app = Flask(__name__)

# supabase config
SUPABASE_URL = "https://dhrxanvrtjzknafcacpf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRocnhhbnZydGp6a25hZmNhY3BmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjQ4OTU0NzMsImV4cCI6MjA0MDQ3MTQ3M30.XZx3n_Xg8m9zP3V4Q2K-Y_T7b0R1S2W3X4Y5Z6A7B8C"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    supabase = None

def get_local_db_data():
    # safely handle sqlite only if running on your local machine
    try:
        import sqlite3
        db_path = os.path.join(os.path.dirname(__file__), 'grader.db')
        if not os.path.exists(db_path):
            return []
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row['name'] for row in cursor.fetchall()]
        results = []
        for table in tables:
            try:
                cursor.execute(f"SELECT * FROM {table}")
                for r in cursor.fetchall():
                    row_dict = dict(r)
                    title = row_dict.get('title') or row_dict.get('name') or row_dict.get('worksheet_name') or f"Worksheet {row_dict.get('id', '')}"
                    results.append({'id': row_dict.get('id', 1), 'title': title, 'type': row_dict.get('type', 'Worksheet')})
            except Exception:
                continue
        conn.close()
        return results
    except Exception:
        return []

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

# routes
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
    data = []
    if supabase:
        try:
            res = supabase.table('assignments').select('*').execute()
            data = res.data or []
        except Exception:
            pass
    if not data:
        data = get_local_db_data()
    return jsonify(data), 200

@app.route('/api/drafts', methods=['GET'])
@app.route('/drafts', methods=['GET'])
def get_drafts():
    return jsonify([]), 200

@app.route('/api/scores', methods=['GET'])
@app.route('/scores', methods=['GET'])
def get_scores():
    return jsonify([]), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)