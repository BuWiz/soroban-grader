import os
import json
import urllib.request
import urllib.parse
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().strip('"').strip("'")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip().strip('"').strip("'")

if SUPABASE_URL and not SUPABASE_URL.startswith("http"):
    SUPABASE_URL = f"https://{SUPABASE_URL}"

def supabase_request(table, method="GET", query_params=None, body=None):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return [] if method == "GET" else None

    endpoint = f"{SUPABASE_URL}/rest/v1/{table}"
    if query_params:
        endpoint += f"?{query_params}"

    data = json.dumps(body).encode('utf-8') if body else None

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    req = urllib.request.Request(endpoint, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as response:
            res_text = response.read().decode('utf-8')
            return json.loads(res_text) if res_text else []
    except Exception as e:
        print(f"Supabase API Error ({table}): {e}")
        return [] if method == "GET" else None

# ----------------- ROUTES ----------------- #

@app.route('/')
def home():
    due_worksheets = supabase_request("worksheets", "GET", "status=eq.assigned&order=created_at.desc") or []
    completed_grades = supabase_request("grades", "GET", "order=timestamp.desc") or []
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

        payload = {
            "title": title,
            "content": content,
            "assignment_type": assignment_type,
            "operation": operation,
            "digits": digits,
            "flash_speed": flash_speed,
            "status": status
        }
        supabase_request("worksheets", "POST", body=payload)
        return redirect(url_for('teacher'))

    drafts = supabase_request("worksheets", "GET", "status=eq.draft&order=created_at.desc") or []
    assigned = supabase_request("worksheets", "GET", "status=eq.assigned&order=created_at.desc") or []
    grades = supabase_request("grades", "GET", "order=timestamp.desc") or []

    return render_template('teacher.html', drafts=drafts, assigned=assigned, grades=grades)

@app.route('/publish/<int:worksheet_id>', methods=['POST'])
def publish_worksheet(worksheet_id):
    supabase_request("worksheets", "PATCH", f"id=eq.{worksheet_id}", body={"status": "assigned"})
    return redirect(url_for('teacher'))

@app.route('/generate_remedial/<int:grade_id>', methods=['POST'])
def generate_remedial(grade_id):
    res = supabase_request("grades", "GET", f"id=eq.{grade_id}&limit=1")
    if res and len(res) > 0:
        grade = res[0]
        missed_problems = grade.get('missed_problems', '')
        original_title = grade.get('worksheet_title', 'Worksheet')
        operation = grade.get('operation', 'Addition')
        digits = grade.get('digits', '1-Digit')
        assignment_type = grade.get('assignment_type', 'standard')

        payload = {
            "title": f"Remedial Practice: {original_title}",
            "content": missed_problems if missed_problems else "Reinforcement Drill",
            "assignment_type": assignment_type,
            "operation": operation,
            "digits": digits,
            "status": "assigned"
        }
        supabase_request("worksheets", "POST", body=payload)

    return redirect(url_for('teacher'))

@app.route('/worksheet')
@app.route('/worksheet/<int:worksheet_id>')
def worksheet(worksheet_id=None):
    sheet = None
    if worksheet_id:
        res = supabase_request("worksheets", "GET", f"id=eq.{worksheet_id}&limit=1")
        sheet = res[0] if res else None
        
    if not sheet:
        res = supabase_request("worksheets", "GET", "status=eq.assigned&order=created_at.desc&limit=1")
        sheet = res[0] if res else None

    return render_template('worksheet.html', worksheet=sheet or {})

@app.route('/flash_worksheet')
@app.route('/flash_worksheet/<int:worksheet_id>')
def flash_worksheet(worksheet_id=None):
    if worksheet_id is None:
        worksheet_id = request.args.get('id', type=int)

    sheet = None
    if worksheet_id:
        res = supabase_request("worksheets", "GET", f"id=eq.{worksheet_id}&limit=1")
        sheet = res[0] if res else None
        
    if not sheet:
        res = supabase_request("worksheets", "GET", "assignment_type=eq.flash&order=created_at.desc&limit=1")
        sheet = res[0] if res else None
        
    if not sheet:
        res = supabase_request("worksheets", "GET", "status=eq.assigned&order=created_at.desc&limit=1")
        sheet = res[0] if res else None

    return render_template('flash_worksheet.html', worksheet=sheet or {})

@app.route('/submit_grade', methods=['POST'])
def submit_grade():
    student_name = request.form.get('student_name', 'Anonymous Student')
    worksheet_id = request.form.get('worksheet_id')
    worksheet_title = request.form.get('worksheet_title', 'Soroban Worksheet')
    score = request.form.get('score')
    missed_problems = request.form.get('missed_problems', '')
    
    sheet = None
    if worksheet_id:
        res = supabase_request("worksheets", "GET", f"id=eq.{worksheet_id}&limit=1")
        sheet = res[0] if res else None

    operation = sheet.get('operation', 'Addition') if sheet else 'Addition'
    digits = sheet.get('digits', '1-Digit') if sheet else '1-Digit'
    assignment_type = sheet.get('assignment_type', 'standard') if sheet else 'standard'
    
    payload = {
        "student_name": student_name,
        "worksheet_id": int(worksheet_id) if worksheet_id else None,
        "worksheet_title": worksheet_title,
        "operation": operation,
        "digits": digits,
        "assignment_type": assignment_type,
        "score": str(score),
        "missed_problems": missed_problems
    }
    supabase_request("grades", "POST", body=payload)

    return jsonify({"status": "success", "message": "Grade recorded successfully!"})

@app.route('/results')
def results():
    all_grades = supabase_request("grades", "GET", "order=timestamp.desc") or []
    return render_template('results.html', grades=all_grades)

if __name__ == '__main__':
    app.run(debug=True)