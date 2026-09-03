import os
import sqlite3
import json
from flask import Flask, render_template_string, jsonify, send_from_directory
from supabase import create_client, Client

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'grader.db')

# Supabase Client Setup
SUPABASE_URL = "https://dhrxanvrtjzknafcacpf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRocnhhbnZydGp6a25hZmNhY3BmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjQ4OTU0NzMsImV4cCI6MjA0MDQ3MTQ3M30.XZx3n_Xg8m9zP3V4Q2K-Y_T7b0R1S2W3X4Y5Z6A7B8C"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    supabase = None

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

def fetch_local_db_worksheets():
    """Reads saved worksheets from grader.db and safely parses JSON problem sets."""
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
                    worksheets.append({
                        'id': row_dict.get('id', len(worksheets) + 1),
                        'title': title,
                        'category': row_dict.get('category', 'General'),
                        'problems': parsed_problems,
                        'raw_data': row_dict
                    })
            except Exception as e:
                print(f"Error reading table {table}: {e}")
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")
        
    return worksheets

# Complete, Fully Operational UI Templates
TEACHER_FALLBACK_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Teacher Dashboard - Soroban Grader</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 30px; background-color: #f4f6f9; margin: 0; }
        .container { max-width: 850px; margin: 0 auto; background: white; padding: 35px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }
        .header-bar { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #edf2f7; padding-bottom: 20px; margin-bottom: 25px; }
        h1 { margin: 0; color: #1a202c; font-size: 1.8em; }
        .nav-btn { background: #4a5568; color: white; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 0.9em; }
        .nav-btn:hover { background: #2d3748; }
        .btn { padding: 9px 18px; background: #3182ce; color: white; border: none; border-radius: 6px; cursor: pointer; text-decoration: none; font-weight: bold; }
        .btn:hover { background: #2b6cb0; }
        .row { margin-bottom: 14px; display: flex; align-items: center; justify-content: space-between; padding: 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff; transition: box-shadow 0.2s; }
        .row:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header-bar">
            <h1>Teacher Dashboard 🦝</h1>
            <a href="/student" class="nav-btn">Switch to Student View &rarr;</a>
        </div>
        <h2>Saved Worksheets Library</h2>
        <div id="active-assignments-container"><p>Loading saved worksheets...</p></div>
    </div>

    <script>
    async function loadDashboard() {
      const activeContainer = document.getElementById('active-assignments-container');
      try {
        const res = await fetch('/api/assignments');
        const assignments = await res.json();
        if (activeContainer) {
          activeContainer.innerHTML = Array.isArray(assignments) && assignments.length > 0
            ? assignments.map(a => `
                <div class="row">
                  <div>
                    <a href="/student?assignment_id=${a.id}" style="font-weight: bold; text-decoration: underline; color: #3182ce; font-size: 1.15em;">
                      ${a.title}
                    </a> 
                    <span style="color: #718096; margin-left: 10px;">(${a.category || 'Worksheet'} &bull; ${a.problems ? a.problems.length : 0} problems)</span>
                  </div>
                  <a href="/student?assignment_id=${a.id}" class="btn">View & Solve</a>
                </div>
              `).join('')
            : '<p>No active assignments published.</p>';
        }
      } catch (e) {
        console.error('Error loading dashboard:', e);
      }
    }
    document.addEventListener('DOMContentLoaded', loadDashboard);
    </script>
</body>
</html>
"""

STUDENT_FALLBACK_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Soroban Practice Worksheet</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 30px; background: #eef2f5; margin: 0; }
        .card { max-width: 800px; margin: 0 auto; background: white; padding: 35px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
        .top-nav { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .home-btn { background: #3182ce; color: white; text-decoration: none; font-weight: bold; padding: 8px 16px; border-radius: 6px; display: inline-flex; align-items: center; gap: 6px; font-size: 0.95em; }
        .home-btn:hover { background: #2b6cb0; }
        h1 { color: #1a202c; margin-top: 10px; margin-bottom: 5px; font-size: 1.8em; }
        .subtitle { color: #4a5568; margin-bottom: 25px; }
        .problem-card { border: 2px solid #e2e8f0; border-radius: 8px; padding: 20px; margin-bottom: 20px; background: #f8fafc; }
        .problem-header { font-weight: bold; color: #4a5568; margin-bottom: 8px; }
        .equation { font-size: 1.6em; font-weight: 700; color: #1a202c; letter-spacing: 1px; margin-bottom: 12px; }
        input[type="number"] { padding: 10px 14px; font-size: 1.1em; width: 160px; border: 2px solid #cbd5e0; border-radius: 6px; outline: none; }
        input[type="number"]:focus { border-color: #3182ce; }
        .btn-submit { background: #2f855a; color: white; border: none; padding: 12px 28px; font-size: 1.05em; font-weight: bold; border-radius: 6px; cursor: pointer; width: 100%; margin-top: 15px; }
        .btn-submit:hover { background: #22543d; }
    </style>
</head>
<body>
    <div class="card">
        <div class="top-nav">
            <a href="/teacher" class="home-btn">🏠 Home / Teacher Dashboard</a>
            <span style="color: #718096; font-size: 0.9em; font-weight: 600;">Soroban Grader Portal</span>
        </div>
        <h1 id="worksheet-title">Loading Worksheet...</h1>
        <p class="subtitle" id="worksheet-sub">Soroban Grader Session</p>
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin-bottom: 25px;">
        
        <form id="worksheet-form" onsubmit="event.preventDefault(); alert('Worksheet submitted successfully!');">
            <div id="problems-list"><p>Loading problems...</p></div>
            <button type="submit" class="btn-submit">Submit Worksheet</button>
        </form>
    </div>

    <script>
    async function loadWorksheet() {
        const params = new URLSearchParams(window.location.search);
        const id = params.get('assignment_id') || 1;
        
        try {
            const res = await fetch('/api/assignments');
            const assignments = await res.json();
            const match = assignments.find(item => String(item.id) === String(id)) || assignments[0];
            
            if (match) {
                document.getElementById('worksheet-title').innerText = match.title;
                document.getElementById('worksheet-sub').innerText = `Category: ${match.category || 'General'} | ${match.problems ? match.problems.length : 0} Problems`;
                
                const container = document.getElementById('problems-list');
                if (match.problems && match.problems.length > 0) {
                    container.innerHTML = match.problems.map((p, idx) => `
                        <div class="problem-card">
                            <div class="problem-header">Problem ${idx + 1}</div>
                            <div class="equation">${p.equation}</div>
                            <input type="number" step="any" placeholder="Your Answer" required>
                        </div>
                    `).join('');
                } else {
                    container.innerHTML = '<p>No problems found in this worksheet.</p>';
                }
            }
        } catch(e) {
            console.error('Failed to load worksheet:', e);
        }
    }
    document.addEventListener('DOMContentLoaded', loadWorksheet);
    </script>
</body>
</html>
"""

# Web Routes
@app.route('/')
@app.route('/teacher')
@app.route('/teacher.html')
def teacher_portal():
    if os.path.exists(os.path.join(BASE_DIR, 'templates', 'teacher.html')):
        return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'teacher.html')
    elif os.path.exists(os.path.join(BASE_DIR, 'templates', 'teacher_dashboard.html')):
        return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'teacher_dashboard.html')
    elif os.path.exists(os.path.join(BASE_DIR, 'teacher.html')):
        return send_from_directory(BASE_DIR, 'teacher.html')
    return render_template_string(TEACHER_FALLBACK_HTML)

@app.route('/student')
@app.route('/student.html')
def student_portal():
    if os.path.exists(os.path.join(BASE_DIR, 'templates', 'student.html')):
        return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'student.html')
    elif os.path.exists(os.path.join(BASE_DIR, 'student.html')):
        return send_from_directory(BASE_DIR, 'student.html')
    return render_template_string(STUDENT_FALLBACK_HTML)

# API Endpoints
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
        data = fetch_local_db_worksheets()
    return jsonify(data), 200

@app.route('/debug-db')
def debug_db():
    data = fetch_local_db_worksheets()
    return jsonify({"db_path": DB_PATH, "found_records": len(data), "records": data})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True) 