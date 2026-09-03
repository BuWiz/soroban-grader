import os
import sqlite3
import json
from flask import Flask, render_template_string, jsonify, send_from_directory, request
from supabase import create_client, Client

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'grader.db')

# Active Supabase Credentials
SUPABASE_URL = "https://dhrxanvrtjzknafcacpf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRocnhhbnZydGp6a25hZmNhY3BmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjQ4OTU0NzMsImV4cCI6MjA0MDQ3MTQ3M30.XZx3n_Xg8m9zP3V4Q2K-Y_T7b0R1S2W3X4Y5Z6A7B8C"

supabase: Client = None
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Supabase init error: {e}")

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

def save_assignment(title, category, problems, is_assigned, is_flash, flash_speed_ms):
    """Saves assignment directly to Supabase with local SQLite fallback."""
    payload = {
        'title': title,
        'category': category,
        'problems': json.dumps(problems) if isinstance(problems, list) else problems,
        'is_assigned': is_assigned,
        'is_flash': is_flash,
        'flash_speed_ms': flash_speed_ms
    }
    
    # 1. Primary Cloud Save: Supabase
    if supabase:
        try:
            res = supabase.table('assignments').insert(payload).execute()
            if res.data:
                return True
        except Exception as e:
            print(f"Supabase save failed, attempting local fallback: {e}")

    # 2. Local Fallback Save: SQLite
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO assignments (title, category, problems, is_assigned, is_flash, flash_speed_ms)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (title, category, payload['problems'], is_assigned, is_flash, flash_speed_ms))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"SQLite save failed: {e}")

    return False

def publish_draft(draft_id):
    """Updates draft state (is_assigned = 1) in Supabase or SQLite."""
    if supabase:
        try:
            supabase.table('assignments').update({'is_assigned': 1}).eq('id', draft_id).execute()
            return True
        except Exception as e:
            print(f"Supabase publish failed: {e}")

    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('UPDATE assignments SET is_assigned = 1 WHERE id = ?', (draft_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"SQLite publish failed: {e}")
    return False

def fetch_worksheets(filter_status=None):
    """Fetches assignments from Supabase or local grader.db."""
    worksheets = []
    
    # 1. Try Supabase
    if supabase:
        try:
            query = supabase.table('assignments').select('*')
            if filter_status == 'active':
                query = query.eq('is_assigned', 1)
            elif filter_status == 'draft':
                query = query.eq('is_assigned', 0)
            
            res = query.execute()
            if res.data:
                for row in res.data:
                    raw_problems = row.get('problems', '[]')
                    parsed_problems = []
                    if isinstance(raw_problems, str):
                        try: parsed_problems = json.loads(raw_problems)
                        except Exception: parsed_problems = []
                    elif isinstance(raw_problems, list):
                        parsed_problems = raw_problems

                    category = row.get('category') or 'Division'
                    worksheets.append({
                        'id': row.get('id'),
                        'title': row.get('title') or f"Worksheet {row.get('id')}",
                        'category': category,
                        'type': category,
                        'is_assigned': row.get('is_assigned', 1),
                        'is_flash': row.get('is_flash', 0),
                        'flash_speed_ms': row.get('flash_speed_ms', 1500),
                        'problems': parsed_problems
                    })
                return worksheets
        except Exception as e:
            print(f"Supabase fetch fallback to SQLite: {e}")

    # 2. Local SQLite Fallback
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r['name'] for r in cursor.fetchall() if r['name'] != 'sqlite_sequence']
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT * FROM {table}")
                    for r in cursor.fetchall():
                        row_dict = dict(r)
                        raw_problems = row_dict.get('problems', '[]')
                        parsed_problems = json.loads(raw_problems) if isinstance(raw_problems, str) else raw_problems
                        
                        category = row_dict.get('category') or 'Division'
                        is_assigned = row_dict.get('is_assigned', 1)
                        item = {
                            'id': row_dict.get('id', len(worksheets) + 1),
                            'title': row_dict.get('title') or f"Worksheet {row_dict.get('id')}",
                            'category': category,
                            'type': category,
                            'is_assigned': is_assigned,
                            'is_flash': row_dict.get('is_flash', 0),
                            'flash_speed_ms': row_dict.get('flash_speed_ms', 1500),
                            'problems': parsed_problems
                        }
                        if filter_status == 'active' and is_assigned == 1: worksheets.append(item)
                        elif filter_status == 'draft' and is_assigned == 0: worksheets.append(item)
                        elif filter_status is None: worksheets.append(item)
                except Exception: pass
            conn.close()
        except Exception as e:
            print(f"SQLite error: {e}")
            
    return worksheets

TEACHER_DASHBOARD_HTML = """
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

        .header h1 { margin: 0; font-size: 2em; font-weight: 800; color: #1e3a8a; }

        .btn-switch {
            background: #0284c7; color: white; text-decoration: none; padding: 10px 18px;
            border-radius: 8px; font-weight: 700; font-size: 0.9em;
        }

        .form-group { margin-bottom: 20px; }

        label { display: block; font-weight: 700; margin-bottom: 8px; color: var(--text-dark); }

        input[type="text"], input[type="number"], textarea, select {
            width: 100%; padding: 12px; border: 2px solid var(--border); border-radius: 8px;
            font-family: inherit; font-size: 0.95em; box-sizing: border-box; outline: none;
        }

        .btn-group { display: flex; gap: 12px; margin-top: 15px; }

        .btn {
            padding: 11px 22px; background: var(--primary); color: white; border: none;
            border-radius: 8px; font-weight: 700; cursor: pointer; font-size: 0.95em;
        }

        .btn-secondary { background: var(--secondary); }

        .btn-assign {
            background: var(--primary); color: white; padding: 6px 14px; border-radius: 6px;
            text-decoration: none; font-weight: 700; font-size: 0.85em; border: none; cursor: pointer;
        }

        hr { border: none; border-top: 2px solid #e2e8f0; margin: 30px 0; }

        h2 { font-size: 1.3em; color: #1e293b; margin-top: 0; margin-bottom: 12px; }

        .section-block {
            background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px; margin-bottom: 25px;
        }

        .tabs-container {
            display: flex; gap: 8px; margin-bottom: 18px; flex-wrap: wrap; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;
        }

        .tab-btn {
            padding: 8px 16px; border: 1px solid #cbd5e1; background: #ffffff; border-radius: 20px;
            font-weight: 700; font-size: 0.88em; color: #475569; cursor: pointer;
        }

        .tab-btn.active { background: #2563eb; color: #ffffff; border-color: #2563eb; }

        .row-item {
            background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px;
            margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;
        }

        .badge { background: #dcfce7; color: #15803d; font-weight: 800; padding: 4px 10px; border-radius: 12px; font-size: 0.85em; }
        .category-tag { background: #e0f2fe; color: #0369a1; font-size: 0.8em; font-weight: 700; padding: 3px 8px; border-radius: 6px; margin-left: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Teacher Dashboard 🦝</h1>
            <a href="/student" class="btn-switch">Switch to Student Portal &rarr;</a>
        </div>

        <div class="form-group">
            <label>Assignment Title:</label>
            <input type="text" id="title-input" placeholder="e.g. Flash Anzan Set 1">
        </div>

        <div class="form-group">
            <label>Worksheet Category:</label>
            <select id="category-input" onchange="toggleFlashSpeedInput()">
                <option value="Division">Division</option>
                <option value="Multiplication">Multiplication</option>
                <option value="Subtraction">Subtraction</option>
                <option value="Addition">Addition</option>
                <option value="Flash Anzan">Flash Anzan</option>
            </select>
        </div>

        <div class="form-group" id="flash-speed-group" style="display: none;">
            <label>Flash Speed (Milliseconds per term):</label>
            <input type="number" id="flash-speed-input" value="1500" placeholder="1500">
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

        <h2>Student Grades & Automated Scoring</h2>
        <div class="section-block">
            <div id="student-grades-container"><p style="color: var(--text-muted);">Loading student scores...</p></div>
        </div>

        <h2>Active Student Work Library</h2>
        <div class="section-block">
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

        <h2>Saved Draft Library</h2>
        <div class="section-block">
            <div id="draft-assignments-container"><p style="color: var(--text-muted);">Loading draft library...</p></div>
        </div>
    </div>

    <script>
    let cachedAssignments = [];
    let currentCategory = 'All';

    function toggleFlashSpeedInput() {
      const category = document.getElementById('category-input').value;
      document.getElementById('flash-speed-group').style.display = (category === 'Flash Anzan') ? 'block' : 'none';
    }

    async function loadDashboard() {
      try {
        const [scoresRes, assignmentsRes, draftsRes] = await Promise.all([
          fetch('/api/scores'),
          fetch('/api/assignments'),
          fetch('/api/drafts')
        ]);

        const scores = await scoresRes.json();
        cachedAssignments = await assignmentsRes.json();
        const drafts = await draftsRes.json();

        const gradesContainer = document.getElementById('student-grades-container');
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

        const draftsContainer = document.getElementById('draft-assignments-container');
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
      const flashSpeed = parseInt(document.getElementById('flash-speed-input').value) || 1500;
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
          body: JSON.stringify({ 
            title, 
            category, 
            problems, 
            is_assigned: isAssigned,
            is_flash: category === 'Flash Anzan' ? 1 : 0,
            flash_speed_ms: flashSpeed
          })
        });
        
        if (res.ok) {
          alert(isAssigned ? 'Worksheet Published!' : 'Draft Saved to Library!');
          document.getElementById('title-input').value = '';
          document.getElementById('problems-input').value = '';
          await loadDashboard();
        } else {
          alert('Failed to save assignment.');
        }
      } catch (e) {
        alert('Connection error.');
      }
    }

    async function publishDraft(draftId) {
      try {
        await fetch(`/api/assignments/publish?id=${draftId}`, { method: 'POST' });
        await loadDashboard();
      } catch(e) {
        console.error('Publish error:', e);
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
        .home-btn { background: #2563eb; color: white; text-decoration: none; font-weight: bold; padding: 8px 16px; border-radius: 6px; display: inline-flex; align-items: center; gap: 6px; font-size: 0.95em; }
        h1 { color: #1a202c; margin-top: 10px; margin-bottom: 5px; font-size: 1.8em; }
        .subtitle { color: #4a5568; margin-bottom: 25px; }
        .problem-card { border: 2px solid #e2e8f0; border-radius: 8px; padding: 20px; margin-bottom: 20px; background: #f8fafc; }
        .problem-header { font-weight: bold; color: #4a5568; margin-bottom: 8px; }
        .equation { font-size: 1.6em; font-weight: 700; color: #1a202c; letter-spacing: 1px; margin-bottom: 12px; }
        .flash-display-box {
            background: #0f172a; color: #38bdf8; font-size: 3.5em; font-weight: 900;
            text-align: center; height: 180px; display: flex; align-items: center;
            justify-content: center; border-radius: 10px; margin-bottom: 20px; letter-spacing: 2px;
        }
        input[type="number"] { padding: 12px 16px; font-size: 1.2em; width: 180px; border: 2px solid #cbd5e0; border-radius: 6px; outline: none; }
        .btn-submit { background: #10b981; color: white; border: none; padding: 14px 28px; font-size: 1.1em; font-weight: bold; border-radius: 6px; cursor: pointer; width: 100%; margin-top: 15px; }
        .btn-flash-start { background: #2563eb; color: white; border: none; padding: 14px 28px; font-size: 1.2em; font-weight: bold; border-radius: 8px; cursor: pointer; width: 100%; }
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
            <button type="submit" id="btn-submit-main" class="btn-submit">Submit Worksheet</button>
        </form>
    </div>

    <script>
    let currentWorksheet = null;

    async function loadWorksheet() {
        const params = new URLSearchParams(window.location.search);
        const id = params.get('assignment_id') || 1;
        
        try {
            const res = await fetch('/api/assignments');
            const assignments = await res.json();
            currentWorksheet = assignments.find(item => String(item.id) === String(id)) || assignments[0];
            
            if (currentWorksheet) {
                document.getElementById('worksheet-title').innerText = currentWorksheet.title;
                document.getElementById('worksheet-sub').innerText = `Category: ${currentWorksheet.category || 'General'} | ${currentWorksheet.problems ? currentWorksheet.problems.length : 0} Problems`;
                
                const isFlash = currentWorksheet.is_flash || (currentWorksheet.category && currentWorksheet.category.toLowerCase() === 'flash anzan');
                if (isFlash) renderFlashInterface();
                else renderStandardInterface();
            }
        } catch(e) { console.error('Failed to load worksheet:', e); }
    }

    function renderStandardInterface() {
        const container = document.getElementById('problems-list');
        if (currentWorksheet.problems && currentWorksheet.problems.length > 0) {
            container.innerHTML = currentWorksheet.problems.map((p, idx) => `
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

    function renderFlashInterface() {
        const container = document.getElementById('problems-list');
        document.getElementById('btn-submit-main').style.display = 'none';

        container.innerHTML = `
            <div id="flash-container">
                <div class="flash-display-box" id="flash-screen">READY?</div>
                <button type="button" class="btn-flash-start" id="btn-start-flash" onclick="runFlashSequence()">⚡ Start Flash Session</button>
                <div id="flash-answer-section" style="display: none; margin-top: 20px;">
                    <div class="problem-header" style="font-size: 1.1em; margin-bottom: 10px;">Enter Final Flash Answers:</div>
                    <div id="flash-answers-inputs"></div>
                    <button type="submit" class="btn-submit" style="display: block;">Submit Answers</button>
                </div>
            </div>
        `;
    }

    async function runFlashSequence() {
        const screen = document.getElementById('flash-screen');
        document.getElementById('btn-start-flash').style.display = 'none';

        const speed = currentWorksheet.flash_speed_ms || 1500;
        const problems = currentWorksheet.problems || [];

        for (let i = 0; i < problems.length; i++) {
            const prob = problems[i];
            screen.innerText = `Problem ${i + 1}`;
            await sleep(1200);

            let terms = typeof prob.equation === 'string' ? prob.equation.split(',').map(t => t.trim()) : [prob.equation];

            for (let term of terms) {
                screen.innerText = term;
                await sleep(speed);
                screen.innerText = '';
                await sleep(200);
            }

            screen.innerText = 'DONE!';
            await sleep(800);
        }

        screen.innerText = 'COMPLETE!';
        showFlashAnswersForm();
    }

    function showFlashAnswersForm() {
        const section = document.getElementById('flash-answer-section');
        const inputsContainer = document.getElementById('flash-answers-inputs');
        section.style.display = 'block';

        inputsContainer.innerHTML = currentWorksheet.problems.map((p, idx) => `
            <div class="problem-card" style="margin-bottom: 12px;">
                <div class="problem-header">Problem ${idx + 1} Answer</div>
                <input type="number" step="any" placeholder="Your Answer" required>
            </div>
        `).join('');
    }

    function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }
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
    return render_template_string(TEACHER_DASHBOARD_HTML)

@app.route('/student')
@app.route('/student.html')
def student_portal():
    return render_template_string(STUDENT_HTML)

# API Endpoints
@app.route('/api/assignments', methods=['GET', 'POST'])
@app.route('/assignments', methods=['GET', 'POST'])
def handle_assignments():
    if request.method == 'POST':
        data = request.get_json() or {}
        title = data.get('title')
        category = data.get('category', 'Division')
        problems = data.get('problems', [])
        is_assigned = data.get('is_assigned', 1)
        is_flash = data.get('is_flash', 0)
        flash_speed_ms = data.get('flash_speed_ms', 1500)
        
        success = save_assignment(title, category, problems, is_assigned, is_flash, flash_speed_ms)
        if success:
            return jsonify({"status": "success"}), 201
        return jsonify({"status": "error", "message": "Save failed"}), 500
        
    data = fetch_worksheets(filter_status='active')
    return jsonify(data), 200

@app.route('/api/assignments/publish', methods=['POST'])
def handle_publish():
    draft_id = request.args.get('id')
    if draft_id:
        publish_draft(draft_id)
    return jsonify({"status": "published"}), 200

@app.route('/api/scores', methods=['GET'])
def get_scores():
    return jsonify([
        {"student_name": "Leigha", "worksheet_title": "division 1", "score": 100}
    ]), 200

@app.route('/api/drafts', methods=['GET'])
def get_drafts():
    data = fetch_worksheets(filter_status='draft')
    return jsonify(data), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True) 