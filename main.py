import os
import json
import urllib.request
import urllib.error
from flask import Flask, render_template, request, jsonify, redirect

app = Flask(__name__, template_folder='templates', static_folder='static')

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

@app.route('/teacher', methods=['GET'])
@app.route('/teacher.html', methods=['GET'])
def teacher_portal():
    return render_template('teacher.html')

@app.route('/student', methods=['GET'])
@app.route('/student.html', methods=['GET'])
def student_portal():
    return render_template('student.html')

# ==================== API ENDPOINTS ====================

@app.route('/api/worksheets', methods=['GET', 'POST'])
def handle_worksheets():
    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form.to_dict()
        
        payload = {
            "title": data.get('title', 'Untitled Worksheet').strip(),
            "type": data.get('type', 'Flash Anzan'),
            "operation": data.get('operation', 'Addition'),
            "digits": data.get('digits', '1-Digit'),
            "content": data.get('content', '').strip(),
            "flash_speed": int(data.get('flash_speed', 3000)) if str(data.get('flash_speed', 3000)).isdigit() else 3000,
            "status": data.get('status', 'published')
        }
        
        result = supabase_request('worksheets', method='POST', data=payload)
        if result is not None:
            return jsonify({"status": "success", "data": result}), 201
        return jsonify({"status": "error", "message": "Failed to save worksheet"}), 500
    
    result = supabase_request('worksheets?select=*')
    return jsonify(result if result is not None else [])

@app.route('/api/worksheets/<id>', methods=['DELETE'])
def delete_worksheet(id):
    result = supabase_request(f'worksheets?id=eq.{id}', method='DELETE')
    return jsonify({"status": "success", "data": result})

@app.route('/api/worksheets/publish/<id>', methods=['POST'])
def publish_worksheet(id):
    result = supabase_request(f'worksheets?id=eq.{id}', method='PATCH', data={"status": "published"})
    return jsonify({"status": "success", "data": result})

@app.route('/api/grades', methods=['GET', 'POST'])
def handle_grades():
    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form.to_dict()
        
        payload = {
            "worksheet_id": str(data.get('worksheet_id', '')),
            "student_name": data.get('student_name', 'Leigha'),
            "score": int(data.get('score', 0)),
            "total_problems": int(data.get('total_problems', 0)),
            "details": data.get('details', [])
        }
        
        result = supabase_request('grades', method='POST', data=payload)
        if result is not None:
            return jsonify({"status": "success", "data": result}), 201
        return jsonify({"status": "error", "message": "Failed to save grade"}), 500
    
    result = supabase_request('grades?select=*')
    return jsonify(result if result is not None else [])

if __name__ == '__main__':
    app.run(debug=True) 