import os
import json
import urllib.request
import urllib.error
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__, template_folder='templates', static_folder='static')

# Environment variables setup
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip('/')
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

def supabase_request(endpoint, method="GET", data=None):
    """Helper function to execute REST API requests to Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    payload = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            return json.loads(res_body) if res_body else []
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"Supabase HTTP Error ({e.code}): {error_body}")
        return None
    except Exception as e:
        print(f"Supabase Connection Error: {str(e)}")
        return None

# ==================== PAGE ROUTES ====================

@app.route('/')
def index():
    return render_template('student.html')

@app.route('/teacher', methods=['GET', 'POST'])
@app.route('/teacher.html', methods=['GET', 'POST'])
def teacher_portal():
    if request.method == 'POST':
        # Accept both JSON payload and standard HTML form post
        payload = request.get_json(silent=True) or request.form.to_dict()
        if payload:
            supabase_request('worksheets', method='POST', data=payload)
        return redirect('/teacher')
    return render_template('teacher.html')

@app.route('/student', methods=['GET'])
@app.route('/student.html', methods=['GET'])
def student_portal():
    return render_template('student.html')

# ==================== API ENDPOINTS ====================

@app.route('/api/worksheets', methods=['GET', 'POST'])
def handle_worksheets():
    if request.method == 'POST':
        payload = request.get_json(silent=True) or request.form.to_dict()
        result = supabase_request('worksheets', method='POST', data=payload)
        if result is not None:
            return jsonify({"status": "success", "data": result}), 201
        return jsonify({"status": "error", "message": "Failed to create worksheet"}), 500
    
    # GET request
    result = supabase_request('worksheets?select=*&order=created_at.desc')
    return jsonify(result if result is not None else [])

@app.route('/api/grades', methods=['GET', 'POST'])
def handle_grades():
    if request.method == 'POST':
        payload = request.get_json(silent=True) or request.form.to_dict()
        result = supabase_request('grades', method='POST', data=payload)
        if result is not None:
            return jsonify({"status": "success", "data": result}), 201
        return jsonify({"status": "error", "message": "Failed to save grade"}), 500
    
    # GET request
    result = supabase_request('grades?select=*&order=timestamp.desc')
    return jsonify(result if result is not None else [])

if __name__ == '__main__':
    app.run(debug=True)