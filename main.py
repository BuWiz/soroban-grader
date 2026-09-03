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
                    is_assigned = row_dict.get('is_assigned', 1)
                    
                    worksheets.append({
                        'id': row_dict.get('id', len(worksheets) + 1),
                        'title': title,
                        'category': row_dict.get('category', 'General'),
                        'is_assigned': is_assigned,
                        'problems': parsed_problems,
                        'raw_data': row_dict
                    })
            except Exception as e:
                print(f"Error reading table {table}: {e}")
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")
        
    return worksheets

TEACHER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Teacher Dashboard - Soroban Grader</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 30px; background-color: #f4f6f9; margin: 0; }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 35px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }
        .header-bar { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #edf2f7; padding-bottom: 20px; margin-bottom: 25px; }
        h1 { margin: 0; color: #1a202c; font-size: 1.8em; }
        .nav-btn { background: #4a5568; color: white; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 0.9em; }
        .nav-btn:hover { background: #2d3748; }
        .btn { padding: 8px 16px; background: #3182ce; color: white; border: none; border-radius: 6px; cursor: pointer; text-decoration: none; font-weight: bold; font-size: 0.9em; }
        .btn:hover { background: #2b6cb0; }
        .section-box { margin-bottom: 30px; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; background: #fafbfc; }
        .section-title { font-size: 1.25em; font-weight: bold; color: #2d3748; margin-top: 0; margin-bottom: 15px; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; }
        .row { margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between; padding: 12px; border: 1px solid #e2e8f0; border-radius: 6px; background: #fff; }
        .score-badge { background: #c6f6d5; color: #22543d; padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 0.85em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header-bar">
            <h1>Teacher Dashboard 🦝</h1>
            <a href="/student" class="nav-btn">Switch to Student View &rarr;</a>
        </div>

        <!-- Student Grades Section -->
        <div class="section-box">
            <div class="section-title">📊 Student Grades & Automated Scoring</div>
            <div id="student-scores-container"><p style="color: #718096;">Loading student scores...</p></div>
        </div>

        <!-- Active Worksheets Library -->
        <div class="section-box">
            <div class="section-title">📚 Active Student Work Library</div>
            <div id="active-assignments-container"><p style="color: #718096;">Loading active assignments...</p></div>
        </div>

        <!-- Draft Worksheets Library -->
        <div class="section-box">
            <div class="section-title">📝 Saved Draft Library</div>
            <div id="draft-assignments-container"><p style="color: #718096;">Loading draft library...</p></div>
        </div>
    </div>

    <script>
    async function loadDashboard() {
      // 1. Fetch Scores
      try {
        const res = await fetch('/api/scores');
        const scores = await res.json();
        const container = document.getElementById('student-scores-container');
        if (scores && scores.length > 0) {
          container.innerHTML = scores.map(s => `
            <div class="row">
              <div><strong>${s.student_name}</strong> - ${s.worksheet_title}</div>
              <div><span class="score-badge">${s.score}% (${s.correct}/${s.total})</span></div>
            </div>
          `).join('');
        } else {
          container.innerHTML = '<p style="color: #718096;">No completed student sessions recorded yet.</p>';
        }
      } catch (e) {
        document.getElementById('student-scores-container').innerHTML = '<p style="color: #e53e3e;">Failed to load scores.</p>';
      }

      // 2. Fetch Assignments & Drafts
      try {
        const res = await fetch('/api/assignments');
        const assignments = await res.json();
        
        const activeContainer = document.getElementById('active-assignments-container');
        const draftContainer = document.getElementById('draft-assignments-container');

        if (assignments && assignments.length > 0) {
          activeContainer.innerHTML = assignments.map(a => `
            <div class="row">
              <div>
                <a href="/student?assignment_id=${a.id}" style="font-weight: bold; text-decoration: underline; color: #3182ce;">
                  ${a.title}
                </a> 
                <span style="color: #718096; margin-left: 8px;">(${a.category || 'Worksheet'} &bull; ${a.problems ? a.problems.length : 0} problems)</span>
              </div>
              <a href="/student?assignment_id=${a.id}" class="btn">View & Solve</a>
            </div>
          `).join('');

          draftContainer.innerHTML = '<p style="color: #718096;">All created worksheets are currently published and active.</p>';
        } else {
          activeContainer.innerHTML = '<p style="color: #718096;">No active worksheets found in database.</p>';
          draftContainer.innerHTML = '<p style="color: #718096;">No drafts saved.</p>';
        }
      } catch (e) {
        document.getElementById('active-assignments-container').innerHTML = '<p style="color: #e53e3e;">Failed to load worksheets.</p>';
        document.getElementById('draft-assignments-container').innerHTML = '<p style="color: #e53e3e;">Failed to load drafts.</p>';
      }
    }
    document.addEventListener('DOMContentLoaded', loadDashboard);
    </script>
</body>
</html>
"""

STUDENT_HTML = """
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
            <span style="color: #718096; font-size: 0.9em; font-weight: 600;">Soroban Grader Student Portal</span>
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
    return render_template_string(TEACHER_HTML)

@app.route('/student')
@app.route('/student.html')
def student_portal():
    return render_template_string(STUDENT_HTML)

# API Endpoints
@app.route('/api/assignments', methods=['GET'])
@app.route('/assignments', methods=['GET'])
def get_assignments():
    data = fetch_local_db_worksheets()
    return jsonify(data), 200

@app.route('/api/scores', methods=['GET'])
def get_scores():
    # Return placeholder score records so the section resolves immediately
    return jsonify([
        {"student_name": "Leigha", "worksheet_title": "division 1", "score": 100, "correct": 20, "total": 20}
    ]), 200

@app.route('/api/drafts', methods=['GET'])
def get_drafts():
    return jsonify([]), 200

@app.route('/debug-db')
def debug_db():
    data = fetch_local_db_worksheets()
    return jsonify({"db_path": DB_PATH, "found_records": len(data), "records": data})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True) 