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
    
    # Create tables for worksheets and grades with assignment types support
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS worksheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            filename TEXT,
            assignment_type TEXT DEFAULT 'standard',
            flash_speed TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT,
            worksheet_id INTEGER,
            score TEXT,
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
    conn = get_db()
    worksheets = conn.execute('SELECT * FROM worksheets ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('student.html', worksheets=worksheets)

@app.route('/teacher', methods=['GET', 'POST'])
def teacher():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content', '')
        assignment_type = request.form.get('assignment_type', 'standard')
        flash_speed = request.form.get('flash_speed', '')
        
        # Handle file upload if present
        filename = None
        if 'worksheet_file' in request.files:
            file = request.files['worksheet_file']
            if file and file.filename != '':
                filename = file.filename
                # Save to writeable /tmp on Vercel
                upload_dir = '/tmp/uploads' if os.environ.get('VERCEL') else 'uploads'
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, filename))
        
        # Save worksheet record to DB
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO worksheets (title, content, filename, assignment_type, flash_speed) 
            VALUES (?, ?, ?, ?, ?)
        ''', (title, content, filename, assignment_type, flash_speed))
        conn.commit()
        conn.close()
        
        return redirect(url_for('teacher'))

    # GET request: load teacher dashboard and all active worksheets
    conn = get_db()
    worksheets = conn.execute('SELECT * FROM worksheets ORDER BY created_at DESC').fetchall()
    conn.close()
    
    return render_template('teacher.html', worksheets=worksheets)

@app.route('/worksheet')
@app.route('/worksheet/<int:worksheet_id>')
def worksheet(worksheet_id=None):
    conn = get_db()
    if worksheet_id:
        sheet = conn.execute('SELECT * FROM worksheets WHERE id = ?', (worksheet_id,)).fetchone()
    else:
        sheet = conn.execute('SELECT * FROM worksheets ORDER BY created_at DESC LIMIT 1').fetchone()
    conn.close()
    
    return render_template('worksheet.html', worksheet=sheet)

@app.route('/results')
def results():
    conn = get_db()
    all_grades = conn.execute('SELECT * FROM grades ORDER BY timestamp DESC').fetchall()
    conn.close()
    
    return render_template('results.html', grades=all_grades)

@app.route('/flash_worksheet')
def flash_worksheet():
    return render_template('flash_worksheet.html')

if __name__ == '__main__':
    app.run(debug=True) 