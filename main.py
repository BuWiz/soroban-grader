import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

# Use writeable /tmp directory on Vercel to prevent file permission crashes
DB_PATH = '/tmp/grader.db' if os.environ.get('VERCEL') else 'grader.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Worksheets table supporting drafts, active assignments, and flash settings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS worksheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            filename TEXT,
            assignment_type TEXT DEFAULT 'standard',
            flash_speed TEXT,
            status TEXT DEFAULT 'draft',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Grades table for storing completed auto-graded student submissions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            worksheet_id INTEGER,
            worksheet_title TEXT,
            score TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Initialize database schema on startup
init_db()

# ----------------- ROUTES ----------------- #

@app.route('/')
def home():
    # Render student portal showing only active assigned worksheets
    conn = get_db()
    worksheets = conn.execute("SELECT * FROM worksheets WHERE status = 'assigned' ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template('student.html', worksheets=worksheets)

@app.route('/teacher', methods=['GET', 'POST'])
def teacher():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content', '')
        assignment_type = request.form.get('assignment_type', 'standard')
        flash_speed = request.form.get('flash_speed', '')
        
        # Determine draft vs immediate assign status
        action = request.form.get('action')
        status = 'assigned' if action == 'publish' else 'draft'

        filename = None
        if 'worksheet_file' in request.files:
            file = request.files['worksheet_file']
            if file and file.filename != '':
                filename = file.filename
                upload_dir = '/tmp/uploads' if os.environ.get('VERCEL') else 'uploads'
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, filename))
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO worksheets (title, content, filename, assignment_type, flash_speed, status) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, content, filename, assignment_type, flash_speed, status))
        conn.commit()
        conn.close()
        
        return redirect(url_for('teacher'))

    # GET: Load drafts, active assignments, and student grades
    conn = get_db()
    drafts = conn.execute("SELECT * FROM worksheets WHERE status = 'draft' ORDER BY created_at DESC").fetchall()
    assigned = conn.execute("SELECT * FROM worksheets WHERE status = 'assigned' ORDER BY created_at DESC").fetchall()
    completed_grades = conn.execute("SELECT * FROM grades ORDER BY timestamp DESC").fetchall()
    conn.close()
    
    return render_template('teacher.html', drafts=drafts, assigned=assigned, grades=completed_grades)

@app.route('/publish/<int:worksheet_id>', methods=['POST'])
def publish_worksheet(worksheet_id):
    # Route to convert saved draft into an assigned student worksheet
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE worksheets SET status = 'assigned' WHERE id = ?", (worksheet_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('teacher'))

@app.route('/worksheet')
@app.route('/worksheet/<int:worksheet_id>')
def worksheet(worksheet_id=None):
    conn = get_db()
    sheet = None
    if worksheet_id:
        sheet = conn.execute('SELECT * FROM worksheets WHERE id = ?', (worksheet_id,)).fetchone()
    
    if not sheet:
        sheet = conn.execute("SELECT * FROM worksheets WHERE status = 'assigned' ORDER BY created_at DESC LIMIT 1").fetchone()
    conn.close()

    return render_template('worksheet.html', worksheet=sheet or {})

@app.route('/flash_worksheet')
@app.route('/flash_worksheet/<int:worksheet_id>')
def flash_worksheet(worksheet_id=None):
    if worksheet_id is None:
        worksheet_id = request.args.get('id', type=int)

    conn = get_db()
    sheet = None
    
    # 1. Try fetching by explicit ID
    if worksheet_id:
        sheet = conn.execute('SELECT * FROM worksheets WHERE id = ?', (worksheet_id,)).fetchone()
    
    # 2. Fallback: fetch latest flash assignment
    if not sheet:
        sheet = conn.execute("SELECT * FROM worksheets WHERE assignment_type = 'flash' ORDER BY created_at DESC LIMIT 1").fetchone()
        
    # 3. Final fallback: fetch ANY latest assigned worksheet
    if not sheet:
        sheet = conn.execute("SELECT * FROM worksheets WHERE status = 'assigned' ORDER BY created_at DESC LIMIT 1").fetchone()
        
    conn.close()

    return render_template('flash_worksheet.html', worksheet=sheet or {})

@app.route('/submit_grade', methods=['POST'])
def submit_grade():
    student_name = request.form.get('student_name', 'Anonymous Student')
    worksheet_id = request.form.get('worksheet_id')
    worksheet_title = request.form.get('worksheet_title', 'Soroban Worksheet')
    score = request.form.get('score')
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO grades (student_name, worksheet_id, worksheet_title, score)
        VALUES (?, ?, ?, ?)
    ''', (student_name, worksheet_id, worksheet_title, score))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "success", "message": "Grade recorded successfully!"})

@app.route('/results')
def results():
    conn = get_db()
    all_grades = conn.execute('SELECT * FROM grades ORDER BY timestamp DESC').fetchall()
    conn.close()
    return render_template('results.html', grades=all_grades)

if __name__ == '__main__':
    app.run(debug=True) 