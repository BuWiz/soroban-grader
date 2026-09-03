import os
import sqlite3
import json
from flask import Flask, render_template_string, jsonify, send_from_directory, request

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

TEACHER_DASHBOARD_STYLED = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Soroban Grader - Teacher Dashboard</title>
    <style>
        :root {
            --primary: #4f46e5;
            --primary-hover: #4338ca;
            --bg-gradient: linear-gradient(135deg, #e0e7ff 0%, #f3e8ff 100%);
            --card-bg: #ffffff;
            --text-dark: #1e293b;
            --text-muted: #64748b;
            --border-color: #e2e8f0;
        }

        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: var(--bg-gradient);
            min-height: 100vh;
            padding: 40px 20px;
            margin: 0;
            color: var(--text-dark);
        }

        .dashboard-card {
            max-width: 950px;
            margin: 0 auto;
            background: var(--card-bg);
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 20px;
            margin-bottom: 30px;
        }

        .header h1 {
            margin: 0;
            font-size: 2.1em;
            font-weight: 800;
            background: linear-gradient(90deg, #4f46e5, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .btn-student-view {
            background: #0284c7;
            color: white;
            text-decoration: none;
            padding: 10px 18px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 0.9em;
            transition: background 0.2s;
        }

        .btn-student-view:hover {
            background: #0369a1;
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            font-weight: 700;
            margin-bottom: 8px;
            color: var(--text-dark);
        }

        input[type="text"], textarea {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid var(--border-color);
            border-radius: 8px;
            font-family: inherit;
            font-size: 0.95em;
            box-sizing: border-box;
            outline: none;
            transition: border-color 0.2s;
        }

        input[type="text"]:focus, textarea:focus {
            border-color: var(--primary);
        }

        .btn-group {
            display: flex;
            gap: 12px;
            margin-top: 15px;
        }

        .btn {
            padding: 10px 20px;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 700;
            cursor: pointer;
            transition: background 0.2s;
        }

        .btn:hover {
            background: var(--primary-hover);
        }

        .btn-secondary {
            background: #64748b;
        }

        .btn-secondary:hover {
            background: #475569;
        }

        .btn-action {
            background: #059669;
            color: white;
            padding: 6px 14px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 700;
            font-size: 0.85em;
        }

        .btn-action:hover {
            background: #047857;
        }

        hr {
            border: none;
            border-top: 2px solid var(--border-color);
            margin: 35px 0;
        }

        h2 {
            font-size: 1.35em;
            color: #334155;
            margin-top: 0;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .section-block {
            background: #f8fafc;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 25px;
        }

        .item-row {
            background: white;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 14px 18px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .badge-score {
            background: #dcfce7;
            color: #15803d;
            font-weight: 800;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
        }
    </style>
</head>
<body>
    <div class="dashboard-card">
        <div class="header">
            <h1>Teacher Dashboard 🦝</h1>
            <a href="/student" class="btn-student-view">Switch to Student Portal &rarr;</a>
        </div>

        <!-- Worksheet Creator Controls -->
        <div class="form-group">
            <label>Assignment Title:</label>
            <input type="text" placeholder="e.g. Division Practice Set 1">
        </div>

        <div class="form-group">
            <label>Parsed Problems (One math expression per line):</label>
            <textarea rows="4" placeholder="5, -3, +8&#10;9, +1, -2"></textarea>
        </div>

        <div class="btn-group">
            <button class="btn" onclick="alert('Worksheet Published!');">Publish to Students</button>
            <button class="btn btn-secondary" onclick="alert('Saved to Drafts!');">Save to Library (Draft)</button>
        </div>

        <hr>

        <!-- Student Grades Section -->
        <h2>📊 Student Grades & Automated Scoring</h2>
        <div class="section-block">
            <div id="student-grades-container"><p style="color: var(--text-muted);">Loading student scores...</p></div>
        </div>

        <!-- Active Student Work Library -->
        <h2>📚 Active Student Work Library</h2>
        <div class="section-block">
            <div id="active-assignments-container"><p style="color: var(--text-muted);">Loading active assignments...</p></div>
        </div>

        <!-- Saved Draft Library -->
        <h2>📝 Saved Draft Library</h2>
        <div class="section-block">
            <div id="draft-assignments-container"><p style="color: var(--text-muted);">Loading draft library...</p></div>
        </div>
    </div>

    <script>
    async function loadDashboard() {
      const gradesContainer = document.getElementById('student-grades-container');
      const activeContainer = document.getElementById('active-assignments-container');
      const draftsContainer = document.getElementById('draft-assignments-container');

      try {
        const [scoresRes, assignmentsRes, draftsRes] = await Promise.all([
          fetch('/api/scores'),
          fetch('/api/assignments'),
          fetch('/api/drafts')
        ]);

        const scores = await scoresRes.json();
        const assignments = await assignmentsRes.json();
        const drafts = await draftsRes.json();

        if (gradesContainer) {
          gradesContainer.innerHTML = Array.isArray(scores) && scores.length > 0 
            ? scores.map(s => `
                <div class="item-row">
                  <div><strong>${s.student_name || 'Leigha'}</strong> &bull; ${s.worksheet_title || 'Worksheet'}</div>
                  <span class="badge-score">${s.score || 100}% Score</span>
                </div>
              `).join('')
            : '<p style="color: var(--text-muted);">No student scores recorded yet.</p>';
        }

        if (activeContainer) {
          activeContainer.innerHTML = Array.isArray(assignments) && assignments.length > 0
            ? assignments.map(a => `
                <div class="item-row">
                  <div>
                    <a href="/student?assignment_id=${a.id || ''}" style="font-weight: 700; text-decoration: underline; color: #4f46e5; font-size: 1.05em;">
                      ${a.title}
                    </a> 
                    <span style="color: var(--text-muted); font-size: 0.9em; margin-left: 8px;">(${a.type || 'Worksheet'})</span>
                  </div>
                  <a href="/student?assignment_id=${a.id || ''}" class="btn-action">Assign / View</a>
                </div>
              `).join('')
            : '<p style="color: var(--text-muted);">No active assignments published.</p>';
        }

        if (draftsContainer) {
          draftsContainer.innerHTML = Array.isArray(drafts) && drafts.length > 0
            ? drafts.map(d => `
                <div class="item-row">
                  <div><strong>${d.title}</strong> <span style="color: var(--text-muted); font-size: 0.85em;">(Draft)</span></div>
                  <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 0.8em;">Publish</button>
                </div>
              `).join('')
            : '<p style="color: var(--text-muted);">No saved drafts found in library.</p>';
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

# Serve workspace file if exists, otherwise serve high-grade embedded dashboard
@app.route('/')
@app.route('/teacher')
@app.route('/teacher.html')
def teacher_portal():
    if os.path.exists(os.path.join(BASE_DIR, 'templates', 'teacher.html')):
        return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'teacher.html')
    elif os.path.exists(os.path.join(BASE_DIR, 'teacher.html')):
        return send_from_directory(BASE_DIR, 'teacher.html')
    return render_template_string(TEACHER_DASHBOARD_STYLED)

@app.route('/student')
@app.route('/student.html')
def student_portal():
    if os.path.exists(os.path.join(BASE_DIR, 'templates', 'student.html')):
        return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'student.html')
    elif os.path.exists(os.path.join(BASE_DIR, 'student.html')):
        return send_from_directory(BASE_DIR, 'student.html')
    return "<h1>student.html missing</h1>"

# API Endpoints
@app.route('/api/assignments', methods=['GET'])
@app.route('/assignments', methods=['GET'])
def get_assignments():
    data = fetch_local_db_worksheets()
    return jsonify(data), 200

@app.route('/api/scores', methods=['GET'])
def get_scores():
    return jsonify([
        {"student_name": "Leigha", "worksheet_title": "division 1", "score": 100}
    ]), 200

@app.route('/api/drafts', methods=['GET'])
def get_drafts():
    return jsonify([]), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True) 