import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
from supabase import create_client, Client

app = Flask(__name__)

url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(url, key) if url and key else None

@app.route('/')
def home():
    if supabase:
        try:
            res = supabase.table('worksheets').select('*').eq('status', 'assigned').order('created_at', desc=True).execute()
            due_worksheets = res.data or []
        except Exception:
            due_worksheets = []
            
        try:
            grades_res = supabase.table('grades').select('*').order('timestamp', desc=True).execute()
            completed_grades = grades_res.data or []
        except Exception:
            completed_grades = []
    else:
        due_worksheets, completed_grades = [], []
        
    return render_template('student.html', due_worksheets=due_worksheets, completed_grades=completed_grades)

@app.route('/teacher', methods=['GET', 'POST'])
def teacher():
    if request.method == 'POST':
        title = request.form.get('title', 'Untitled Assignment')
        content = request.form.get('content', '')
        assignment_type = request.form.get('assignment_type', 'standard')
        operation = request.form.get('operation', 'Addition')
        digits = request.form.get('digits', '1-Digit')
        flash_speed = request.form.get('flash_speed', '')
        
        action = request.form.get('action')
        status = 'assigned' if action == 'publish' else 'draft'

        if supabase:
            supabase.table('worksheets').insert({
                "title": title,
                "content": content,
                "assignment_type": assignment_type,
                "operation": operation,
                "digits": digits,
                "flash_speed": flash_speed,
                "status": status
            }).execute()
            
        return redirect(url_for('teacher'))

    if supabase:
        try:
            drafts = supabase.table('worksheets').select('*').eq('status', 'draft').order('created_at', desc=True).execute().data or []
        except Exception:
            drafts = []
            
        try:
            assigned = supabase.table('worksheets').select('*').eq('status', 'assigned').order('created_at', desc=True).execute().data or []
        except Exception:
            assigned = []
            
        try:
            grades = supabase.table('grades').select('*').order('timestamp', desc=True).execute().data or []
        except Exception:
            grades = []
    else:
        drafts, assigned, grades = [], [], []

    return render_template('teacher.html', drafts=drafts, assigned=assigned, grades=grades)

@app.route('/publish/<int:worksheet_id>', methods=['POST'])
def publish_worksheet(worksheet_id):
    if supabase:
        supabase.table('worksheets').update({'status': 'assigned'}).eq('id', worksheet_id).execute()
    return redirect(url_for('teacher'))

@app.route('/generate_remedial/<int:grade_id>', methods=['POST'])
def generate_remedial(grade_id):
    if supabase:
        res = supabase.table('grades').select('*').eq('id', grade_id).limit(1).execute()
        if res.data:
            grade = res.data[0]
            missed_problems = grade.get('missed_problems', '')
            original_title = grade.get('worksheet_title', 'Worksheet')
            operation = grade.get('operation', 'Addition')
            digits = grade.get('digits', '1-Digit')
            assignment_type = grade.get('assignment_type', 'standard')

            remedial_title = f"Remedial Practice: {original_title}"
            remedial_content = missed_problems if missed_problems else "Reinforcement Drill"

            supabase.table('worksheets').insert({
                "title": remedial_title,
                "content": remedial_content,
                "assignment_type": assignment_type,
                "operation": operation,
                "digits": digits,
                "status": "assigned"
            }).execute()

    return redirect(url_for('teacher'))

@app.route('/worksheet')
@app.route('/worksheet/<int:worksheet_id>')
def worksheet(worksheet_id=None):
    sheet = None
    if supabase:
        if worksheet_id:
            res = supabase.table('worksheets').select('*').eq('id', worksheet_id).limit(1).execute()
            sheet = res.data[0] if res.data else None
            
        if not sheet:
            res = supabase.table('worksheets').select('*').eq('status', 'assigned').order('created_at', desc=True).limit(1).execute()
            sheet = res.data[0] if res.data else None

    return render_template('worksheet.html', worksheet=sheet or {})

@app.route('/flash_worksheet')
@app.route('/flash_worksheet/<int:worksheet_id>')
def flash_worksheet(worksheet_id=None):
    if worksheet_id is None:
        worksheet_id = request.args.get('id', type=int)

    sheet = None
    if supabase:
        if worksheet_id:
            res = supabase.table('worksheets').select('*').eq('id', worksheet_id).limit(1).execute()
            sheet = res.data[0] if res.data else None
            
        if not sheet:
            res = supabase.table('worksheets').select('*').eq('assignment_type', 'flash').order('created_at', desc=True).limit(1).execute()
            sheet = res.data[0] if res.data else None
            
        if not sheet:
            res = supabase.table('worksheets').select('*').eq('status', 'assigned').order('created_at', desc=True).limit(1).execute()
            sheet = res.data[0] if res.data else None

    return render_template('flash_worksheet.html', worksheet=sheet or {})

@app.route('/submit_grade', methods=['POST'])
def submit_grade():
    student_name = request.form.get('student_name', 'Anonymous Student')
    worksheet_id = request.form.get('worksheet_id')
    worksheet_title = request.form.get('worksheet_title', 'Soroban Worksheet')
    score = request.form.get('score')
    missed_problems = request.form.get('missed_problems', '')
    
    sheet = None
    if supabase and worksheet_id:
        res = supabase.table('worksheets').select('*').eq('id', worksheet_id).limit(1).execute()
        sheet = res.data[0] if res.data else None

    operation = sheet.get('operation', 'Addition') if sheet else 'Addition'
    digits = sheet.get('digits', '1-Digit') if sheet else '1-Digit'
    assignment_type = sheet.get('assignment_type', 'standard') if sheet else 'standard'
    
    if supabase:
        supabase.table('grades').insert({
            "student_name": student_name,
            "worksheet_id": worksheet_id,
            "worksheet_title": worksheet_title,
            "operation": operation,
            "digits": digits,
            "assignment_type": assignment_type,
            "score": score,
            "missed_problems": missed_problems
        }).execute()

    return jsonify({"status": "success", "message": "Grade recorded successfully!"})

@app.route('/results')
def results():
    all_grades = []
    if supabase:
        res = supabase.table('grades').select('*').order('timestamp', desc=True).execute()
        all_grades = res.data or []
    return render_template('results.html', grades=all_grades)

if __name__ == '__main__':
    app.run(debug=True) 