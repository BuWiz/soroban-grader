import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

DB_URL = os.environ.get('DATABASE_URL')
_db_initialized = False

def get_db():
    if DB_URL:
        conn_str = DB_URL
        if 'sslmode' not in conn_str:
            separator = '&' if '?' in conn_str else '?'
            conn_str = f"{conn_str}{separator}sslmode=require"
        return psycopg2.connect(conn_str, cursor_factory=RealDictCursor)
    else:
        conn = sqlite3.connect('grader.db')
        conn.row_factory = sqlite3.Row
        return conn

def execute_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = get_db()
    cursor = conn.cursor()
    
    if DB_URL:
        query = query.replace('?', '%s')
        
    cursor.execute(query, params)
    
    result = None
    if fetchone:
        result = cursor.fetchone()
    elif fetchall:
        result = cursor.fetchall()
        
    if commit:
        conn.commit()
        
    cursor.close()
    conn.close()
    return result

def init_db():
    global _db_initialized
    if _db_initialized:
        return
        
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        if DB_URL:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS worksheets (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT,
                    filename TEXT,
                    assignment_type TEXT DEFAULT 'standard',
                    flash_speed TEXT,
                    status TEXT DEFAULT 'draft',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS grades (
                    id SERIAL PRIMARY KEY,
                    student_name TEXT NOT NULL,
                    worksheet_id INTEGER,
                    worksheet_title TEXT,
                    score TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
        else:
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
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS grades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_name TEXT NOT NULL,
                    worksheet_id INTEGER,
                    worksheet_title TEXT,
                    score TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            ''')
        conn.commit()
        cursor.close()
        conn.close()
        _db_initialized = True
    except Exception as e:
        print(f"Database setup error: {e}")

@app.before_request
def setup_db_on_first_request():
    init_db()

# ----------------- ROUTES ----------------- #

@app.route('/')
def home():
    try:
        worksheets = execute_query("SELECT * FROM worksheets WHERE status = 'assigned' ORDER BY created_at DESC", fetchall=True)
    except Exception:
        worksheets = []
    return render_template('student.html', worksheets=worksheets or [])

@app.route('/teacher', methods=['GET', 'POST'])
def teacher():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content', '')
        assignment_type = request.form.get('assignment_type', 'standard')
        flash_speed = request.form.get('flash_speed', '')
        
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
        
        execute_query('''
            INSERT INTO worksheets (title, content, filename, assignment_type, flash_speed, status) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, content, filename, assignment_type, flash_speed, status), commit=True)
        
        return redirect(url_for('teacher'))

    try:
        drafts = execute_query("SELECT * FROM worksheets WHERE status = 'draft' ORDER BY created_at DESC", fetchall=True)
        assigned = execute_query("SELECT * FROM worksheets WHERE status = 'assigned' ORDER BY created_at DESC", fetchall=True)
        completed_grades = execute_query("SELECT * FROM grades ORDER BY timestamp DESC", fetchall=True)
    except Exception:
        drafts, assigned, completed_grades = [], [], []
    
    return render_template('teacher.html', drafts=drafts or [], assigned=assigned or [], grades=completed_grades or [])

@app.route('/publish/<int:worksheet_id>', methods=['POST'])
def publish_worksheet(worksheet_id):
    execute_query("UPDATE worksheets SET status = 'assigned' WHERE id = ?", (worksheet_id,), commit=True)
    return redirect(url_for('teacher'))

@app.route('/worksheet')
@app.route('/worksheet/<int:worksheet_id>')
def worksheet(worksheet_id=None):
    sheet = None
    if worksheet_id:
        sheet = execute_query('SELECT * FROM worksheets WHERE id = ?', (worksheet_id,), fetchone=True)
    
    if not sheet:
        sheet = execute_query("SELECT * FROM worksheets WHERE status = 'assigned' ORDER BY created_at DESC LIMIT 1", fetchone=True)

    return render_template('worksheet.html', worksheet=sheet or {})

@app.route('/flash_worksheet')
@app.route('/flash_worksheet/<int:worksheet_id>')
def flash_worksheet(worksheet_id=None):
    if worksheet_id is None:
        worksheet_id = request.args.get('id', type=int)

    sheet = None
    if worksheet_id:
        sheet = execute_query('SELECT * FROM worksheets WHERE id = ?', (worksheet_id,), fetchone=True)
    
    if not sheet:
        sheet = execute_query("SELECT * FROM worksheets WHERE assignment_type = 'flash' ORDER BY created_at DESC LIMIT 1", fetchone=True)
        
    if not sheet:
        sheet = execute_query("SELECT * FROM worksheets WHERE status = 'assigned' ORDER BY created_at DESC LIMIT 1", fetchone=True)

    return render_template('flash_worksheet.html', worksheet=sheet or {})

@app.route('/submit_grade', methods=['POST'])
def submit_grade():
    student_name = request.form.get('student_name', 'Anonymous Student')
    worksheet_id = request.form.get('worksheet_id')
    worksheet_title = request.form.get('worksheet_title', 'Soroban Worksheet')
    score = request.form.get('score')
    
    execute_query('''
        INSERT INTO grades (student_name, worksheet_id, worksheet_title, score)
        VALUES (?, ?, ?, ?)
    ''', (student_name, worksheet_id, worksheet_title, score), commit=True)
    
    return jsonify({"status": "success", "message": "Grade recorded successfully!"})

@app.route('/results')
def results():
    all_grades = execute_query('SELECT * FROM grades ORDER BY timestamp DESC', fetchall=True)
    return render_template('results.html', grades=all_grades or [])

if __name__ == '__main__':
    app.run(debug=True) 