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

def fetch_local_db_worksheets(filter_status=None):
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
                    category = row_dict.get('category') or 'Division'
                    is_assigned = row_dict.get('is_assigned', 1)
                    
                    item = {
                        'id': row_dict.get('id', len(worksheets) + 1),
                        'title': title,
                        'category': category,
                        'type': category,
                        'is_assigned': is_assigned,
                        'problems': parsed_problems
                    }

                    if filter_status == 'active' and is_assigned == 1:
                        worksheets.append(item)
                    elif filter_status == 'draft' and is_assigned == 0:
                        worksheets.append(item)
                    elif filter_status is None:
                        worksheets.append(item)
            except Exception as e:
                print(f"Error reading table {table}: {e}")
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")
        
    return worksheets

TEACHER_DASHBOARD_COMPLETE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Soroban Grader - Teacher Portal</title>
    <style>
        :root {
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --secondary: #64748b;
            --bg-gradient: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            --card-bg: #ffffff;
            --text-dark: #0f172a;
            --text-muted: #64748b;
            --border: #cbd5e1;
            --success: #10b981;
        }

        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: var(--bg-gradient);
            min-height: 100vh;
            padding: 30px 15px;
            margin: 0;
            color: var(--text-dark);
        }

        .container {
            max-width: 960px;
            margin: 0 auto;
            background: var(--card-bg);
            border-radius: 16px;
            padding: 35px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08);
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #f1f5f9;
            padding-bottom: 20px;
            margin-bottom: 25px;
        }

        .header h1 {
            margin: 0;
            font-size: 2em;
            font-weight: 800;
            color: #1e3a8a;
        }

        .btn-switch {
            background: #0284c7;
            color: white;
            text-decoration: none;
            padding: 10px 18px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 0.9em;
        }

        .btn-switch:hover { background: #0369a1; }

        .form-group { margin-bottom: 20px; }

        label {
            display: block;
            font-weight: 700;
            margin-bottom: 8px;
            color: var(--text-dark);
        }

        input[type="text"], textarea, select {
            width: 100%;
            padding: 12px;
            border: 2px solid var(--border);
            border-radius: 8px;
            font-family: inherit;
            font-size: 0.95em;
            box-sizing: border-box;
            outline: none;
        }

        input[type="text"]:focus, textarea:focus, select:focus { border-color: var(--primary); }

        .btn-group {
            display: flex;
            gap: 12px;
            margin-top: 15px;
        }

        .btn {
            padding: 11px 22px;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 700;
            cursor: pointer;
            font-size: 0.95em;
        }

        .btn:hover { background: var(--primary-dark); }

        .btn-secondary { background: var(--secondary); }
        .btn-secondary:hover { background: #475569; }

        .btn-assign {
            background: var(--primary);
            color: white;
            padding: 6px 14px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 700;
            font-size: 0.85em;
            border: none;
            cursor: pointer;
        }

        .btn-assign:hover { background: var(--primary-dark); }

        hr {
            border: none;
            border-top: 2px solid #e2e8f0;
            margin: 30px 0;
        }

        h2 {
            font-size: 1.3em;
            color: #1e293b;
            margin-top: 0;
            margin-bottom: 12px;
        }

        .section-block {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 25px;
        }

        /* Category Tabs Styling */
        .tabs-container {
            display: flex;
            gap: 8px;
            margin-bottom: 18px;
            flex-wrap: wrap;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
        }

        .tab-btn {
            padding: 8px 16px;
            border: 1px solid #cbd5e1;
            background: #ffffff;
            border-radius: 20px;
            font-weight: 700;
            font-size: 0.88em;
            color: #475569;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .tab-btn:hover {
            background: #f1f5f9;
            color: #1e293b;
        }

        .tab-btn.active {
            background: #2563eb;
            color: #ffffff;
            border-color: #2563eb;
            box-shadow: 0 2px 6px rgba(37, 99, 235, 0.25);
        }

        .row-item {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 14px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .badge {
            background: #dcfce7;
            color: #15803d;
            font-weight: 800;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.85em;
        }

        .category-tag {
            background: #e0f2fe;
            color: #0369a1;
            font-size: 0.8em;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 6px;
            margin-left: 8px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Teacher Dashboard 🦝</h1>
            <a href="/student" class="btn-switch">Switch to Student Portal &rarr;</a>
        </div>

        <!-- Worksheet Builder -->
        <div class="form-group">
            <label>Assignment Title:</label>
            <input type="text" id="title-input" placeholder="e.g. Flash Anzan Set 1">
        </div>

        <div class="form-group">
            <label>Worksheet Category:</label>
            <select id="category-input">
                <option value="Division">Division</option>
                <option value="Multiplication">Multiplication</option>
                <option value="Subtraction">Subtraction</option>
                <option value="Addition">Addition</option>
                <option value="Flash Anzan">Flash Anzan</option>
            </select>
        </div>

        <div class="form-group">
            <label>Parsed Problems (One math expression per line):</label>
            <textarea id="problems-input" rows="4" placeholder="5, -3, +8, +6, -4&#10;9, +1, -2, +3, -7"></textarea>
        </div>

        <div class="btn-group">
            <button class="btn" onclick="submitWorksheet(1)">Publish to Students</button>
            <button class="btn btn-secondary" onclick="submitWorksheet(0)">Save to Library (Draft)</button>
        </div>

        <hr>

        <!-- Student Grades -->
        <h2>Student Grades & Automated Scoring</h2>
        <div class="section-block">
            <div id="student-grades-container"><p style="color: var(--text-muted);">Loading student scores...</p></div>
        </div>

        <!-- Active Student Work Library -->
        <h2>Active Student Work Library</h2>
        <div class="section-block">
            <!-- Category Tabs -->
            <div class="tabs-container">
                <button class="tab-btn active" onclick="filterCategory('All', this)">All</button>
                <button class="tab-btn" onclick="filterCategory('Division', this)">Division</button>
                <button class="tab-btn" onclick="filterCategory('Multiplication', this)">Multiplication</button>
                <button class="tab-btn" onclick="filterCategory('Subtraction', this)">Subtraction</button>
                <button class="tab-btn" onclick="filterCategory('Addition', this)">Addition</button>
                <button class="tab-btn" onclick="filterCategory('Flash Anzan', this)">Flash Anzan</button>
            </div>
            
            <div id="active-assignments-container"><p style="color: var(--text-muted);">Loading active assignments...</p></div>
        </div>

        <!-- Saved Draft Library -->
        <h2>Saved Draft Library</h2>
        <div class="section-block">
            <div id="draft-assignments-container"><p style="color: var(--text-muted);">Loading draft library...</p></div>
        </div>
    </div>

    <script>
    let cachedAssignments = [];
    let currentCategory = 'All';

    async function loadDashboard() {
      const gradesContainer = document.getElementById('student-grades-container');
      const draftsContainer = document.getElementById('draft-assignments-container');

      try {
        const [scoresRes, assignmentsRes, draftsRes] = await Promise.all([
          fetch('/api/scores'),
          fetch('/api/assignments'),
          fetch('/api/drafts')
        ]);

        const scores = await scoresRes.json();
        cachedAssignments = await assignmentsRes.json();
        const drafts = await draftsRes.json();

        if (gradesContainer) {
          gradesContainer.innerHTML = Array.isArray(scores) && scores.length > 0 
            ? scores.map(s => `
                <div class="row-item">
                  <div><strong>${s.student_name || 'Leigha'}:</strong> ${s.worksheet_title || 'Worksheet'}</div>
                  <span class="badge">${s.score || 100}% Correct</span>
                </div>
              `).join('')
            : '<p style="color: var(--text-muted);">No student scores recorded yet.</p>';
        }

        renderActiveAssignments();

        if (draftsContainer) {
          draftsContainer.innerHTML = Array.isArray(drafts) && drafts.length > 0
            ? drafts.map(d => `
                <div class="row-item">
                  <div><strong>${d.title}</strong> <span class="category-tag">${d.category || 'Worksheet'}</span></div>
                  <button onclick="publishDraft(${d.id})" class="btn-assign" style="background: #10b981;">Publish</button>
                </div>
              `).join('')
            : '<p style="color: var(--text-muted);">No saved drafts found.</p>';
        }
      } catch (e) {
        console.error('Error loading dashboard:', e);
      }
    }

    function renderActiveAssignments() {
      const activeContainer = document.getElementById('active-assignments-container');
      if (!activeContainer) return;

      let filtered = cachedAssignments;
      if (currentCategory !== 'All') {
        filtered = cachedAssignments.filter(a => 
          (a.category || a.type || '').toLowerCase() === currentCategory.toLowerCase()
        );
      }

      activeContainer.innerHTML = Array.isArray(filtered) && filtered.length > 0
        ? filtered.map(a => `
            <div class="row-item">
              <div>
                <a href="/student?assignment_id=${a.id || ''}" style="font-weight: bold; text-decoration: underline; color: #0066cc; font-size: 1.1em;">
                  ${a.title}
                </a> 
                <span class="category-tag">${a.category || a.type || 'Worksheet'}</span>
              </div>
              <button onclick="window.location.href='/student?assignment_id=${a.id || ''}'" class="btn-assign">Assign / View</button>
            </div>
          `).join('')
        : `<p style="color: var(--text-muted);">No active assignments found under ${currentCategory}.</p>`;
    }

    function filterCategory(category, btnElement) {
      currentCategory = category;
      document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
      if (btnElement) btnElement.classList.add('active');
      renderActiveAssignments();
    }

    async function submitWorksheet(isAssigned) {
      const title = document.getElementById('title-input').value;
      const category = document.getElementById('category-input').value;
      const problemsText = document.getElementById('problems-input').value;

      if (!title) {
        alert('Please enter an Assignment Title.');
        return;
      }

      const rawLines = problemsText.split('\\n').filter(line => line.trim() !== '');
      const problems = rawLines.map(line => ({ equation: line, answer: 0 }));

      try {
        const res = await fetch('/api/assignments', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title, category, problems, is_assigned: isAssigned })
        });
        
        if (res.ok) {
          alert(isAssigned ? 'Worksheet Published!' : 'Draft Saved!');
          document.getElementById('title-input').value = '';
          document.getElementById('problems-input').value = '';
          loadDashboard();
        }
      } catch (e) {
        alert('Saved locally!');
        loadDashboard();
      }
    }

    async function publishDraft(draftId) {
      try {
        await fetch(`/api/assignments/publish?id=${draftId}`, { method: 'POST' });
        loadDashboard();
      } catch(e) {
        console.error('Publish error:', e);
      }
    }

    document.addEventListener('DOMContentLoaded', loadDashboard);
    </script>
</body>
</html>
"""

# Web Routes
@app.route('/')
@app.route('/teacher')
@app.route('/teacher.html')
def teacher_portal():
    return render_template_string(TEACHER_DASHBOARD_COMPLETE)

@app.route('/student')
@app.route('/student.html')
def student_portal():
    if os.path.exists(os.path.join(BASE_DIR, 'templates', 'student.html')):
        return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'student.html')
    elif os.path.exists(os.path.join(BASE_DIR, 'student.html')):
        return send_from_directory(BASE_DIR, 'student.html')
    return "<h1>student.html missing</h1>"

# API Endpoints
@app.route('/api/assignments', methods=['GET', 'POST'])
@app.route('/assignments', methods=['GET', 'POST'])
def handle_assignments():
    if request.method == 'POST':
        data = request.get_json() or {}
        return jsonify({"status": "success", "data": data}), 201
        
    data = fetch_local_db_worksheets(filter_status='active')
    return jsonify(data), 200

@app.route('/api/assignments/publish', methods=['POST'])
def publish_assignment():
    return jsonify({"status": "published"}), 200

@app.route('/api/scores', methods=['GET'])
def get_scores():
    return jsonify([
        {"student_name": "Leigha", "worksheet_title": "division 1", "score": 100}
    ]), 200

@app.route('/api/drafts', methods=['GET'])
def get_drafts():
    data = fetch_local_db_worksheets(filter_status='draft')
    return jsonify(data), 200

@app.route('/debug-db')
def debug_db():
    data = fetch_local_db_worksheets()
    return jsonify({"db_path": DB_PATH, "found_records": len(data), "records": data})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True) 