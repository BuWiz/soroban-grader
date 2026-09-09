import os
from flask import Flask, render_template_string

app = Flask(__name__)

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
            --bg-gradient: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
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
            border-radius: 20px;
            padding: 35px;
            box-shadow: 0 20px 35px rgba(0, 0, 0, 0.15);
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #f1f5f9;
            padding-bottom: 20px;
            margin-bottom: 25px;
        }

        .header h1 { margin: 0; font-size: 2.2em; font-weight: 800; color: #1e3a8a; }

        .btn-switch {
            background: linear-gradient(135deg, #0284c7, #2563eb); color: white; text-decoration: none; padding: 12px 20px;
            border-radius: 10px; font-weight: 700; font-size: 0.95em; cursor: pointer; display: inline-block;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3); border: none;
        }

        .form-group { margin-bottom: 20px; }

        label { display: block; font-weight: 700; margin-bottom: 8px; color: var(--text-dark); }

        input[type="text"], input[type="number"], textarea, select {
            width: 100%; padding: 12px; border: 2px solid var(--border); border-radius: 10px;
            font-family: inherit; font-size: 0.95em; box-sizing: border-box; outline: none;
        }

        .btn-group { display: flex; gap: 12px; margin-top: 15px; }

        .btn {
            padding: 12px 24px; background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; border: none;
            border-radius: 10px; font-weight: 700; cursor: pointer; font-size: 0.95em;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
        }

        .btn-secondary { background: linear-gradient(135deg, #64748b, #475569); box-shadow: 0 4px 12px rgba(100, 116, 139, 0.3); }

        .btn-assign {
            background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; padding: 8px 16px; border-radius: 8px;
            text-decoration: none; font-weight: 700; font-size: 0.88em; border: none; cursor: pointer;
        }

        hr { border: none; border-top: 2px solid #e2e8f0; margin: 30px 0; }

        h2 { font-size: 1.35em; color: #1e293b; margin-top: 0; margin-bottom: 14px; }

        .section-block {
            background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 22px; margin-bottom: 25px;
        }

        .tabs-container {
            display: flex; gap: 8px; margin-bottom: 18px; flex-wrap: wrap; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px;
        }

        .tab-btn {
            padding: 8px 18px; border: 1px solid #cbd5e1; background: #ffffff; border-radius: 20px;
            font-weight: 700; font-size: 0.88em; color: #475569; cursor: pointer; transition: all 0.2s;
        }

        .tab-btn.active { background: #2563eb; color: #ffffff; border-color: #2563eb; box-shadow: 0 3px 8px rgba(37, 99, 235, 0.3); }

        .row-item {
            background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px;
            margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.03);
        }

        .badge { background: #dcfce7; color: #15803d; font-weight: 800; padding: 5px 12px; border-radius: 12px; font-size: 0.85em; }
        .category-tag { background: #e0f2fe; color: #0369a1; font-size: 0.8em; font-weight: 700; padding: 4px 10px; border-radius: 8px; margin-left: 8px; }
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
            <input type="text" id="title-input" placeholder="e.g. Addition Set 1">
        </div>

        <div class="form-group">
            <label>Worksheet Category:</label>
            <select id="category-input" onchange="toggleFlashSpeedInput()">
                <option value="Addition">Addition</option>
                <option value="Division">Division</option>
                <option value="Multiplication">Multiplication</option>
                <option value="Subtraction">Subtraction</option>
                <option value="Flash Anzan">Flash Anzan</option>
            </select>
        </div>

        <div class="form-group" id="flash-speed-group" style="display: none;">
            <label>Flash Speed (Milliseconds per term):</label>
            <input type="number" id="flash-speed-input" value="1500" placeholder="1500">
        </div>

        <div class="form-group">
            <label>Parsed Problems (One math expression per line):</label>
            <textarea id="problems-input" rows="4" placeholder="5, +3, +8, +6, +4&#10;9, +1, +2, +3, +7"></textarea>
        </div>

        <div class="btn-group">
            <button class="btn" onclick="submitWorksheet(1)">Submit to Students</button>
            <button class="btn btn-secondary" onclick="submitWorksheet(0)">Save to Library (Draft)</button>
        </div>

        <hr>

        <h2>Student Grades & Automated Scoring</h2>
        <div class="section-block">
            <div id="student-grades-container">
                <div class="row-item">
                    <div><strong>Leigha:</strong> division 1</div>
                    <span class="badge">100% Correct</span>
                </div>
            </div>
        </div>

        <h2>Active Student Work Library</h2>
        <div class="section-block">
            <div class="tabs-container">
                <button class="tab-btn active" onclick="filterCategory('All', this)">All</button>
                <button class="tab-btn" onclick="filterCategory('Addition', this)">Addition</button>
                <button class="tab-btn" onclick="filterCategory('Division', this)">Division</button>
                <button class="tab-btn" onclick="filterCategory('Multiplication', this)">Multiplication</button>
                <button class="tab-btn" onclick="filterCategory('Subtraction', this)">Subtraction</button>
                <button class="tab-btn" onclick="filterCategory('Flash Anzan', this)">Flash Anzan</button>
            </div>
            <div id="active-assignments-container"></div>
        </div>

        <h2>Saved Draft Library</h2>
        <div class="section-block">
            <div id="draft-assignments-container"></div>
        </div>
    </div>

    <script>
    const INITIAL_ASSIGNMENTS = [
      { id: '1', title: "addition 1", category: "Addition", type: "Addition", is_assigned: 1, problems: [{equation: "15 + 27", answer: 42}, {equation: "34 + 18", answer: 52}] },
      { id: '2', title: "division 1", category: "Division", type: "Division", is_assigned: 1, problems: [{equation: "12 / 3", answer: 4}] },
      { id: '3', title: "2dgt by 2 dgt multiplication", category: "Multiplication", type: "Multiplication", is_assigned: 0, problems: [{equation: "12 x 15", answer: 180}] },
      { id: '4', title: "100s (-) 3", category: "Subtraction", type: "Subtraction", is_assigned: 0, problems: [{"equation": "100 - 3", "answer": 97}] },
      { id: '5', title: "100s (-) 4", category: "Subtraction", type: "Subtraction", is_assigned: 0, problems: [{"equation": "100 - 4", "answer": 96}] },
      { id: '6', title: "Flash Anzan Level 1", category: "Flash Anzan", type: "Flash Anzan", is_assigned: 1, is_flash: 1, flash_speed_ms: 1200, problems: [{"equation": "5, +3, -2, +4", "answer": 10}] }
    ];

    let store = [];
    let currentCategory = 'All';

    function loadStore() {
      const saved = localStorage.getItem('soroban_worksheets_v2');
      if (saved) {
        try { store = JSON.parse(saved); } catch(e) { store = INITIAL_ASSIGNMENTS; }
      } else {
        store = INITIAL_ASSIGNMENTS;
        saveStore();
      }
      renderAll();
    }

    function saveStore() {
      localStorage.setItem('soroban_worksheets_v2', JSON.stringify(store));
    }

    function toggleFlashSpeedInput() {
      const category = document.getElementById('category-input').value;
      document.getElementById('flash-speed-group').style.display = (category === 'Flash Anzan') ? 'block' : 'none';
    }

    function renderAll() {
      renderActiveAssignments();
      renderDrafts();
    }

    function renderActiveAssignments() {
      const activeContainer = document.getElementById('active-assignments-container');
      if (!activeContainer) return;

      let activeItems = store.filter(item => item.is_assigned === 1);
      if (currentCategory !== 'All') {
        activeItems = activeItems.filter(a => 
          (a.category || a.type || '').toLowerCase() === currentCategory.toLowerCase()
        );
      }

      activeContainer.innerHTML = activeItems.length > 0
        ? activeItems.map(a => `
            <div class="row-item">
              <div>
                <a href="/student?assignment_id=${a.id}" style="font-weight: bold; text-decoration: underline; color: #2563eb; font-size: 1.1em;">
                  ${a.title}
                </a> 
                <span class="category-tag">${a.category || 'Worksheet'}</span>
              </div>
              <button onclick="window.location.href='/student?assignment_id=${a.id}'" class="btn-assign">Assign / View</button>
            </div>
          `).join('')
        : `<p style="color: var(--text-muted);">No active assignments found under ${currentCategory}.</p>`;
    }

    function renderDrafts() {
      const draftsContainer = document.getElementById('draft-assignments-container');
      if (!draftsContainer) return;

      let draftItems = store.filter(item => item.is_assigned === 0);

      draftsContainer.innerHTML = draftItems.length > 0
        ? draftItems.map(d => `
            <div class="row-item">
              <div><strong>${d.title}</strong> <span class="category-tag">${d.category || 'Worksheet'}</span></div>
              <button onclick="submitDraftDirectly('${d.id}')" class="btn-assign" style="background: linear-gradient(135deg, #10b981, #059669);">Submit</button>
            </div>
          `).join('')
        : '<p style="color: var(--text-muted);">No saved drafts found.</p>';
    }

    function filterCategory(category, btnElement) {
      currentCategory = category;
      document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
      if (btnElement) btnElement.classList.add('active');
      renderActiveAssignments();
    }

    function submitDraftDirectly(draftId) {
      const target = store.find(d => String(d.id) === String(draftId));
      if (target) {
        target.is_assigned = 1;
        saveStore();
        renderAll();
      }
    }

    function submitWorksheet(isAssigned) {
      const title = document.getElementById('title-input').value;
      const category = document.getElementById('category-input').value;
      const flashSpeed = parseInt(document.getElementById('flash-speed-input').value) || 1500;
      const problemsText = document.getElementById('problems-input').value;

      if (!title) {
        alert('Please enter an Assignment Title.');
        return;
      }

      const rawLines = problemsText.split('\\n').filter(line => line.trim() !== '');
      const problems = rawLines.length > 0 
        ? rawLines.map(line => ({ equation: line, answer: 0 }))
        : [{ equation: "10 + 5", answer: 15 }];

      const newItem = {
        id: String(Date.now()),
        title,
        category,
        type: category,
        is_assigned: isAssigned,
        is_flash: category === 'Flash Anzan' ? 1 : 0,
        flash_speed_ms: flashSpeed,
        problems
      };

      store.push(newItem);
      saveStore();
      renderAll();

      document.getElementById('title-input').value = '';
      document.getElementById('problems-input').value = '';
      alert(isAssigned ? 'Worksheet Submitted to Active Library!' : 'Draft Saved to Library!');
    }

    document.addEventListener('DOMContentLoaded', loadStore);
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
        :root {
            --bg-gradient: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
        }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            padding: 30px 15px; 
            background: var(--bg-gradient); 
            min-height: 100vh;
            margin: 0; 
            box-sizing: border-box;
        }
        .card { 
            max-width: 820px; 
            margin: 0 auto; 
            background: white; 
            padding: 35px; 
            border-radius: 20px; 
            box-shadow: 0 20px 35px rgba(0,0,0,0.15); 
        }
        .top-nav { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            margin-bottom: 20px; 
            flex-wrap: wrap;
            gap: 12px;
        }
        .home-btn { 
            background: linear-gradient(135deg, #2563eb, #1d4ed8); 
            color: white; 
            border: none;
            font-weight: bold; 
            padding: 10px 18px; 
            border-radius: 10px; 
            display: inline-flex; 
            align-items: center; 
            gap: 6px; 
            font-size: 0.95em; 
            cursor: pointer; 
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
        }
        .select-assignment { 
            padding: 10px 14px; 
            border-radius: 8px; 
            border: 2px solid #cbd5e1; 
            font-weight: bold; 
            color: #1e293b; 
            background: #f8fafc; 
            cursor: pointer; 
            outline: none;
        }
        h1 { color: #1e3a8a; margin-top: 10px; margin-bottom: 5px; font-size: 2em; font-weight: 800; }
        .subtitle { color: #64748b; margin-bottom: 25px; font-weight: 600; }
        .problem-card { 
            border: 2px solid #e2e8f0; 
            border-radius: 12px; 
            padding: 22px; 
            margin-bottom: 20px; 
            background: #f8fafc; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.02);
        }
        .problem-header { font-weight: bold; color: #3b82f6; margin-bottom: 8px; font-size: 1.05em; }
        .equation { font-size: 2em; font-weight: 800; color: #0f172a; letter-spacing: 1px; margin-bottom: 14px; }
        .flash-display-box {
            background: linear-gradient(135deg, #0f172a, #1e293b); 
            color: #38bdf8; 
            font-size: 4em; 
            font-weight: 900;
            text-align: center; 
            height: 200px; 
            display: flex; 
            align-items: center;
            justify-content: center; 
            border-radius: 16px; 
            margin-bottom: 20px; 
            letter-spacing: 2px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        }
        input[type="number"] { 
            padding: 12px 16px; 
            font-size: 1.2em; 
            width: 200px; 
            border: 2px solid #cbd5e0; 
            border-radius: 8px; 
            outline: none; 
            font-weight: 700;
        }
        input[type="number"]:focus { border-color: #2563eb; }
        .btn-submit { 
            background: linear-gradient(135deg, #10b981, #059669); 
            color: white; 
            border: none; 
            padding: 16px 28px; 
            font-size: 1.15em; 
            font-weight: bold; 
            border-radius: 10px; 
            cursor: pointer; 
            width: 100%; 
            margin-top: 15px; 
            box-shadow: 0 4px 14px rgba(16, 185, 129, 0.3);
        }
        .btn-flash-start { 
            background: linear-gradient(135deg, #2563eb, #1d4ed8); 
            color: white; 
            border: none; 
            padding: 16px 28px; 
            font-size: 1.25em; 
            font-weight: bold; 
            border-radius: 12px; 
            cursor: pointer; 
            width: 100%; 
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3);
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="top-nav">
            <button type="button" class="home-btn" onclick="window.location.href='/teacher'">🏠 Home / Teacher Dashboard</button>
            <div>
                <label style="font-weight: bold; margin-right: 6px; font-size: 0.9em; color: #475569;">Switch Assignment:</label>
                <select id="assignment-picker" class="select-assignment" onchange="switchAssignment(this.value)">
                </select>
            </div>
        </div>
        <h1 id="worksheet-title">Loading Worksheet...</h1>
        <p class="subtitle" id="worksheet-sub">Soroban Grader Session</p>
        <hr style="border: none; border-top: 2px solid #f1f5f9; margin-bottom: 25px;">
        
        <form id="worksheet-form" onsubmit="event.preventDefault(); alert('Worksheet submitted successfully!');">
            <div id="problems-list"><p>Loading problems...</p></div>
            <button type="submit" id="btn-submit-main" class="btn-submit">Submit Worksheet</button>
        </form>
    </div>

    <script>
    let currentWorksheet = null;
    let allAssigned = [];

    function loadWorksheet() {
        const params = new URLSearchParams(window.location.search);
        const id = params.get('assignment_id');
        
        const saved = localStorage.getItem('soroban_worksheets_v2');
        let store = [];
        if (saved) {
            try { store = JSON.parse(saved); } catch(e) {}
        }

        allAssigned = store.filter(item => item.is_assigned === 1);
        if (allAssigned.length === 0) {
            allAssigned = store;
        }

        const picker = document.getElementById('assignment-picker');
        if (picker && allAssigned.length > 0) {
            picker.innerHTML = allAssigned.map(item => `
                <option value="${item.id}" ${String(item.id) === String(id) ? 'selected' : ''}>
                    ${item.title} (${item.category || 'General'})
                </option>
            `).join('');
        }

        if (id) {
            currentWorksheet = store.find(item => String(item.id) === String(id));
        }
        if (!currentWorksheet && allAssigned.length > 0) {
            currentWorksheet = allAssigned[0];
        }

        if (!currentWorksheet) {
            currentWorksheet = {
                id: '1',
                title: 'addition 1',
                category: 'Addition',
                problems: [{ equation: "15 + 27", answer: 42 }]
            };
        }

        document.getElementById('worksheet-title').innerText = currentWorksheet.title || 'Worksheet';
        
        let rawProblems = currentWorksheet.problems || [];
        if (typeof rawProblems === 'string') {
            try { rawProblems = JSON.parse(rawProblems); } catch(e) { rawProblems = []; }
        }
        currentWorksheet.problems = rawProblems;

        document.getElementById('worksheet-sub').innerText = `Category: ${currentWorksheet.category || 'General'} | ${currentWorksheet.problems.length} Problems`;
        
        const isFlash = currentWorksheet.is_flash || (currentWorksheet.category && currentWorksheet.category.toLowerCase() === 'flash anzan');
        if (isFlash) renderFlashInterface();
        else renderStandardInterface();
    }

    function switchAssignment(newId) {
        window.location.href = `/student?assignment_id=${newId}`;
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

@app.route('/')
@app.route('/teacher')
@app.route('/teacher.html')
def teacher_portal():
    return render_template_string(TEACHER_DASHBOARD_HTML)

@app.route('/student')
@app.route('/student.html')
def student_portal():
    return render_template_string(STUDENT_HTML)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)