import os
import sqlite3
import json
from flask import Flask, render_template, send_from_directory, jsonify, request

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'grader.db')

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

def fetch_local_db_worksheets():
    """Reads saved worksheets from grader.db and safely formats for teacher.html JS."""
    if not os.path.exists(DB_PATH):
        return []
    
    worksheets = []
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row['name'] for row in cursor.fetchall() if row['name'] != 'sqlite_sequence']
        
        for table in tables:
            try:
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                for r in rows:
                    row_dict = dict(r)
                    
                    raw_problems = row_dict.get('problems', '[]')
                    parsed_problems = []
                    if isinstance(raw_problems, str):
                        try:
                            parsed_problems = json.loads(raw_problems)
                        except Exception:
                            parsed_problems = []
                    elif isinstance(raw_problems, list):
                        parsed_problems = raw_problems

                    title = row_dict.get('title') or row_dict.get('name') or f"Worksheet {row_dict.get('id', '')}"
                    category = row_dict.get('category') or 'Worksheet'
                    
                    worksheets.append({
                        'id': row_dict.get('id', len(worksheets) + 1),
                        'title': title,
                        'type': category,
                        'problems': parsed_problems
                    })
            except Exception as e:
                print(f"Error reading table {table}: {e}")
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")
        
    return worksheets

# Web Routes - Serves your workspace templates directly
@app.route('/')
@app.route('/teacher')
@app.route('/teacher.html')
def teacher_portal():
    if os.path.exists(os.path.join(BASE_DIR, 'templates', 'teacher.html')):
        return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'teacher.html')
    elif os.path.exists(os.path.join(BASE_DIR, 'teacher.html')):
        return send_from_directory(BASE_DIR, 'teacher.html')
    return "<h1>teacher.html not found in templates directory</h1>"

@app.route('/student')
@app.route('/student.html')
def student_portal():
    if os.path.exists(os.path.join(BASE_DIR, 'templates', 'student.html')):
        return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'student.html')
    elif os.path.exists(os.path.join(BASE_DIR, 'student.html')):
        return send_from_directory(BASE_DIR, 'student.html')
    return "<h1>student.html not found in templates directory</h1>"

# API Endpoints required by teacher.html Promise.all
@app.route('/api/assignments', methods=['GET'])
@app.route('/assignments', methods=['GET'])
def get_assignments():
    data = fetch_local_db_worksheets()
    return jsonify(data), 200

@app.route('/api/scores', methods=['GET'])
def get_scores():
    # Valid JSON array prevents Promise.all from breaking
    return jsonify([]), 200

@app.route('/api/drafts', methods=['GET'])
def get_drafts():
    # Valid JSON array prevents Promise.all from breaking
    return jsonify([]), 200

@app.route('/debug-db')
def debug_db():
    data = fetch_local_db_worksheets()
    return jsonify({"db_path": DB_PATH, "found_records": len(data), "records": data})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True) 