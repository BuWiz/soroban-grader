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
            --bg-gradient: linear-gradient(135deg, #b2e2f8 0%, #e0e7ff 100%);
            --card-bg: #ffffff;
            --text-dark: #1e293b;
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
            border-radius: 24px;
            padding: 35px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.08);
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #f1f5f9;
            padding-bottom: 20px;
            margin-bottom: 25px;
        }

        .header h1 { margin: 0; font-size: 2.2em; font-weight: 800; color: #312e81; }

        .btn-switch {
            background: #2563eb; color: white; text-decoration: none; padding: 12px 22px;
            border-radius: 14px; font-weight: 800; font-size: 0.95em; cursor: pointer; display: inline-block;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3); border: none;
        }

        .form-group { margin-bottom: 20px; }

        label { display: block; font-weight: 700; margin-bottom: 8px; color: var(--text-dark); }

        input[type="text"], input[type="number"], textarea, select {
            width: 100%; padding: 12px; border: 2px solid var(--border); border-radius: 12px;
            font-family: inherit; font-size: 0.95em; box-sizing: border-box; outline: none;
        }

        .btn-group { display: flex; gap: 12px; margin-top: 15px; }

        .btn {
            padding: 12px 24px; background: #2563eb; color: white; border: none;
            border-radius: 12px; font-weight: 700; cursor: pointer; font-size: 0.95em;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3);
        }

        .btn-secondary { background: #64748b; }

        .btn-assign {
            background: #10b981; color: white; padding: 8px 18px; border-radius: 10px;
            text-decoration: none; font-weight: 800; font-size: 0.88em; border: none; cursor: pointer;
        }

        hr { border: none; border-top: 2px solid #e2e8f0; margin: 30px 0; }

        h2 { font-size: 1.35em; color: #1e293b; margin-top: 0; margin-bottom: 14px; font-weight: 800; }

        .section-block {
            background: #f8fafc; border: 2px solid #e2e8f0; border-radius: 16px; padding: 22px; margin-bottom: 25px;
        }

        .tabs-container {
            display: flex; gap: 8px; margin-bottom: 18px; flex-wrap: wrap; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px;
        }

        .tab-btn {
            padding: 8px 18px; border: 1px solid #cbd5e1; background: #ffffff; border-radius: 20px;
            font-weight: 700; font-size: 0.88em; color: #475569; cursor: pointer; transition: all 0.2s;
        }

        .tab-btn.active { background: #2563eb; color: #ffffff; border-color: #2563eb; }

        .row-item {
            background: white; border: 2px solid #e2e8f0; border-radius: 12px; padding: 16px;
            margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;
        }

        .badge { background: #dcfce7; color: #15803d; font-weight: 800; padding: 5px 12px; border-radius: 12px; font-size: 0.85em; }
        .category-tag { background: #e0f2fe; color: #0369a1; font-size: 0.8em; font-weight: 800; padding: 4px 10px; border-radius: 8px; margin-left: 8px; }
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
            <textarea id="problems-input" rows="5" placeholder="12 x 15&#10;24 x 11&#10;35 x 14&#10;42 x 18&#10;56 x 23"></textarea>
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
    const HARDCODED_10_PROBLEMS = [
      { 
        id: '1', 
        title: "addition 1", 
        category: "Addition", 
        type: "Addition", 
        is_assigned: 1, 
        problems: [
          {equation: "15 + 27", answer: 42}, {equation: "34 + 18", answer: 52}, {equation: "49 + 23", answer: 72},
          {equation: "67 + 15", answer: 82}, {equation: "88 + 24", answer: 112}, {equation: "53 + 39", answer: 92},
          {equation: "76 + 18", answer: 94}, {equation: "29 + 64", answer: 93}, {equation: "81 + 19", answer: 100},
          {equation: "95 + 47", answer: 142}
        ] 
      },
      { 
        id: '2', 
        title: "division 1", 
        category: "Division", 
        type: "Division", 
        is_assigned: 1, 
        problems: [
          {equation: "12 / 3", answer: 4}, {equation: "24 / 6", answer: 4}, {equation: "45 / 5", answer: 9},
          {equation: "72 / 8", answer: 9}, {equation: "81 / 9", answer: 9}, {equation: "36 / 4", answer: 9},
          {equation: "48 / 6", answer: 8}, {equation: "56 / 7", answer: 8}, {equation: "63 / 9", answer: 7},
          {equation: "90 / 10", answer: 9}
        ] 
      },
      { 
        id: '3', 
        title: "2dgt by 2 dgt multiplication", 
        category: "Multiplication", 
        type: "Multiplication", 
        is_assigned: 1, 
        problems: [
          {equation: "12 x 15", answer: 180}, {equation: "24 x 11", answer: 264}, {equation: "35 x 14", answer: 490},
          {equation: "42 x 18", answer: 756}, {equation: "56 x 23", answer: 1288}, {equation: "64 x 31", answer: 1984},
          {equation: "15 x 15", answer: 225}, {equation: "22 x 25", answer: 550}, {equation: "30 x 45", answer: 1350},
          {equation: "50 x 12", answer: 600}
        ] 
      },
      { 
        id: '4', 
        title: "100s (-) 3", 
        category: "Subtraction", 
        type: "Subtraction", 
        is_assigned: 1, 
        problems: [
          {equation: "100 - 3", answer: 97}, {equation: "100 - 14", answer: 86}, {equation: "100 - 27", answer: 73},
          {equation: "100 - 42", answer: 58}, {equation: "100 - 65", answer: 35}, {equation: "100 - 78", answer: 22},
          {equation: "100 - 89", answer: 11}, {equation: "100 - 33", answer: 67}, {equation: "100 - 51", answer: 49},
          {equation: "100 - 92", answer: 8}
        ] 
      }
    ];

    let store = HARDCODED_10_PROBLEMS;
    let currentCategory = 'All';

    function loadStore() {
      const saved = localStorage.getItem('soroban_assignments_store');
      if (saved) {
        try { store = JSON.parse(saved); } catch(e) { store = HARDCODED_10_PROBLEMS; }
      } else {
        store = HARDCODED_10_PROBLEMS;
        localStorage.setItem('soroban_assignments_store', JSON.stringify(store));
      }
      renderAll();
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
        : `<p style="color: #64748b;">No active assignments found under ${currentCategory}.</p>`;
    }

    function renderDrafts() {
      const draftsContainer = document.getElementById('draft-assignments-container');
      if (!draftsContainer) return;

      let draftItems = store.filter(item => item.is_assigned === 0);

      draftsContainer.innerHTML = draftItems.length > 0
        ? draftItems.map(d => `
            <div class="row-item">
              <div><strong>${d.title}</strong> <span class="category-tag">${d.category || 'Worksheet'}</span></div>
              <button onclick="submitDraftDirectly('${d.id}')" class="btn-assign">Submit</button>
            </div>
          `).join('')
        : '<p style="color: #64748b;">No saved drafts found.</p>';
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
        localStorage.setItem('soroban_assignments_store', JSON.stringify(store));
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
      localStorage.setItem('soroban_assignments_store', JSON.stringify(store));
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
    <title>Soroban Student Portal</title>
    <style>
        body { 
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: #b2e2f8; 
            min-height: 100vh;
            margin: 0; 
            padding: 30px 15px;
            box-sizing: border-box;
        }

        .portal-wrapper {
            max-width: 820px;
            margin: 0 auto;
        }

        .header-title {
            text-align: center;
            color: #ffffff;
            font-size: 2.8em;
            font-weight: 900;
            margin-top: 0;
            margin-bottom: 25px;
            text-shadow: 3px 3px 0px #3b82f6, 6px 6px 0px rgba(0,0,0,0.08);
            letter-spacing: 1px;
        }

        .top-nav {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .home-btn {
            background: #2563eb;
            color: white;
            border: none;
            font-weight: 800;
            padding: 10px 20px;
            border-radius: 12px;
            cursor: pointer;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }

        .card-section {
            background: #ffffff;
            border-radius: 20px;
            overflow: hidden;
            margin-bottom: 25px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.06);
        }

        .card-header-pink {
            background: #ffb6c1;
            color: #d63384;
            padding: 16px 24px;
            font-size: 1.3em;
            font-weight: 800;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .card-header-green {
            background: #a3e635;
            color: #3f6212;
            padding: 16px 24px;
            font-size: 1.3em;
            font-weight: 800;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .card-body {
            padding: 25px;
        }

        .assignment-row {
            background: #f8fafc;
            border: 2px solid #e2e8f0;
            border-radius: 14px;
            padding: 18px 22px;
            margin-bottom: 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .assignment-row:last-child { margin-bottom: 0; }

        .assignment-title {
            font-size: 1.2em;
            font-weight: 800;
            color: #1e293b;
        }

        .category-badge {
            background: #e0f2fe;
            color: #0369a1;
            font-weight: 800;
            padding: 4px 10px;
            border-radius: 8px;
            font-size: 0.85em;
            margin-left: 8px;
        }

        .btn-start {
            background: #2563eb;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 10px;
            font-weight: 800;
            cursor: pointer;
        }

        .problem-card {
            background: #f8fafc;
            border: 2px solid #e2e8f0;
            border-radius: 14px;
            padding: 20px;
            margin-bottom: 20px;
        }

        .problem-header {
            font-weight: 800;
            color: #2563eb;
            margin-bottom: 10px;
        }

        .equation {
            font-size: 2.2em;
            font-weight: 900;
            color: #0f172a;
            margin-bottom: 15px;
        }

        input[type="number"] {
            padding: 12px 16px;
            font-size: 1.2em;
            width: 200px;
            border: 2px solid #cbd5e1;
            border-radius: 10px;
            font-weight: 800;
            outline: none;
        }

        .btn-submit-all {
            background: #10b981;
            color: white;
            border: none;
            padding: 16px;
            font-size: 1.2em;
            font-weight: 800;
            border-radius: 12px;
            cursor: pointer;
            width: 100%;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="portal-wrapper">
        <div class="top-nav">
            <button class="home-btn" onclick="window.location.href='/teacher'">🏠 Teacher Dashboard</button>
            <button class="home-btn" id="back-to-portal-btn" style="display: none; background: #64748b;" onclick="window.location.href='/student'">&larr; Back to Student Portal Home</button>
        </div>

        <h1 class="header-title">✨ Soroban Student Portal ✨</h1>

        <div id="portal-main-view">
            <div class="card-section">
                <div class="card-header-pink">
                    📌 Due Assignments
                </div>
                <div class="card-body" id="due-assignments-list">
                    <p style="color: #64748b;">Loading pending assignments...</p>
                </div>
            </div>

            <div class="card-section">
                <div class="card-header-green">
                    🌸 Completed History
                </div>
                <div class="card-body" id="completed-assignments-list">
                    <p style="color: #64748b;">No completed assignments yet.</p>
                </div>
            </div>
        </div>

        <div id="worksheet-active-view" style="display: none;">
            <div class="card-section">
                <div class="card-header-pink" id="active-worksheet-title">
                    Worksheet Practice
                </div>
                <div class="card-body">
                    <form id="worksheet-form" onsubmit="handleFormSubmit(event)">
                        <div id="problems-container"></div>
                        <button type="submit" class="btn-submit-all">Submit Worksheet</button>
                    </form>
                </div>
            </div>
        </div>
    </div>

    <script>
    const HARDCODED_10_PROBLEMS = [
      { 
        id: '1', 
        title: "addition 1", 
        category: "Addition", 
        type: "Addition", 
        is_assigned: 1, 
        problems: [
          {equation: "15 + 27", answer: 42}, {equation: "34 + 18", answer: 52}, {equation: "49 + 23", answer: 72},
          {equation: "67 + 15", answer: 82}, {equation: "88 + 24", answer: 112}, {equation: "53 + 39", answer: 92},
          {equation: "76 + 18", answer: 94}, {equation: "29 + 64", answer: 93}, {equation: "81 + 19", answer: 100},
          {equation: "95 + 47", answer: 142}
        ] 
      },
      { 
        id: '2', 
        title: "division 1", 
        category: "Division", 
        type: "Division", 
        is_assigned: 1, 
        problems: [
          {equation: "12 / 3", answer: 4}, {equation: "24 / 6", answer: 4}, {equation: "45 / 5", answer: 9},
          {equation: "72 / 8", answer: 9}, {equation: "81 / 9", answer: 9}, {equation: "36 / 4", answer: 9},
          {equation: "48 / 6", answer: 8}, {equation: "56 / 7", answer: 8}, {equation: "63 / 9", answer: 7},
          {equation: "90 / 10", answer: 9}
        ] 
      },
      { 
        id: '3', 
        title: "2dgt by 2 dgt multiplication", 
        category: "Multiplication", 
        type: "Multiplication", 
        is_assigned: 1, 
        problems: [
          {equation: "12 x 15", answer: 180}, {equation: "24 x 11", answer: 264}, {equation: "35 x 14", answer: 490},
          {equation: "42 x 18", answer: 756}, {equation: "56 x 23", answer: 1288}, {equation: "64 x 31", answer: 1984},
          {equation: "15 x 15", answer: 225}, {equation: "22 x 25", answer: 550}, {equation: "30 x 45", answer: 1350},
          {equation: "50 x 12", answer: 600}
        ] 
      },
      { 
        id: '4', 
        title: "100s (-) 3", 
        category: "Subtraction", 
        type: "Subtraction", 
        is_assigned: 1, 
        problems: [
          {equation: "100 - 3", answer: 97}, {equation: "100 - 14", answer: 86}, {equation: "100 - 27", answer: 73},
          {equation: "100 - 42", answer: 58}, {equation: "100 - 65", answer: 35}, {equation: "100 - 78", answer: 22},
          {equation: "100 - 89", answer: 11}, {equation: "100 - 33", answer: 67}, {equation: "100 - 51", answer: 49},
          {equation: "100 - 92", answer: 8}
        ] 
      }
    ];

    let store = [];
    let completedHistory = [];
    let currentWorksheet = null;

    function initStudentPortal() {
        const savedAssignments = localStorage.getItem('soroban_assignments_store');
        if (savedAssignments) {
            try { store = JSON.parse(savedAssignments); } catch(e) { store = HARDCODED_10_PROBLEMS; }
        } else {
            store = HARDCODED_10_PROBLEMS;
            localStorage.setItem('soroban_assignments_store', JSON.stringify(store));
        }

        const savedCompleted = localStorage.getItem('soroban_completed_history');
        if (savedCompleted) {
            try { completedHistory = JSON.parse(savedCompleted); } catch(e) { completedHistory = []; }
        }

        const params = new URLSearchParams(window.location.search);
        const activeId = params.get('assignment_id');

        if (activeId) {
            currentWorksheet = store.find(item => String(item.id) === String(activeId)) || 
                               completedHistory.find(item => String(item.id) === String(activeId));
            if (currentWorksheet) {
                renderWorksheetView(currentWorksheet);
                return;
            }
        }

        renderPortalHome();
    }

    function renderPortalHome() {
        document.getElementById('portal-main-view').style.display = 'block';
        document.getElementById('worksheet-active-view').style.display = 'none';
        document.getElementById('back-to-portal-btn').style.display = 'none';

        const dueContainer = document.getElementById('due-assignments-list');
        const activeItems = store.filter(item => item.is_assigned === 1);

        if (activeItems.length > 0) {
            dueContainer.innerHTML = activeItems.map(item => `
                <div class="assignment-row">
                    <div>
                        <span class="assignment-title">${item.title}</span>
                        <span class="category-badge">${item.category || 'General'}</span>
                    </div>
                    <button class="btn-start" onclick="window.location.href='/student?assignment_id=${item.id}'">Start Assignment</button>
                </div>
            `).join('');
        } else {
            dueContainer.innerHTML = '<p style="color: #64748b;">No due assignments right now!</p>';
        }

        const completedContainer = document.getElementById('completed-assignments-list');
        if (completedHistory.length > 0) {
            completedContainer.innerHTML = completedHistory.map(item => `
                <div class="assignment-row">
                    <div>
                        <a href="/student?assignment_id=${item.id}" class="assignment-title" style="text-decoration: underline; color: #1e293b;">${item.title}</a>
                        <span class="category-badge">${item.category || 'General'}</span>
                    </div>
                    <span style="color: #16a34a; font-weight: 900;">${item.score || '100%'} Score</span>
                </div>
            `).join('');
        } else {
            completedContainer.innerHTML = '<p style="color: #64748b;">No completed assignments yet.</p>';
        }
    }

    function renderWorksheetView(worksheet) {
        document.getElementById('portal-main-view').style.display = 'none';
        document.getElementById('worksheet-active-view').style.display = 'block';
        document.getElementById('back-to-portal-btn').style.display = 'inline-block';

        document.getElementById('active-worksheet-title').innerText = worksheet.title;

        let problems = worksheet.problems || [];
        if (typeof problems === 'string') {
            try { problems = JSON.parse(problems); } catch(e) { problems = []; }
        }

        const container = document.getElementById('problems-container');
        container.innerHTML = problems.map((p, idx) => `
            <div class="problem-card">
                <div class="problem-header">Problem ${idx + 1}</div>
                <div class="equation">${p.equation}</div>
                <input type="number" step="any" placeholder="Your Answer" required>
            </div>
        `).join('');
    }

    function handleFormSubmit(e) {
        e.preventDefault();
        if (currentWorksheet) {
            currentWorksheet.is_assigned = 0;
            currentWorksheet.score = "100%";

            // Move from active store to completed history
            store = store.filter(item => String(item.id) !== String(currentWorksheet.id));
            completedHistory.unshift(currentWorksheet);

            localStorage.setItem('soroban_assignments_store', JSON.stringify(store));
            localStorage.setItem('soroban_completed_history', JSON.stringify(completedHistory));

            alert('Worksheet submitted successfully!');
            window.location.href = '/student';
        }
    }

    document.addEventListener('DOMContentLoaded', initStudentPortal);
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