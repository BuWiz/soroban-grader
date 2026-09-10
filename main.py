import os
from flask import Flask, render_template

app = Flask(__name__, template_folder='../templates' if os.path.exists('../templates') else 'templates')

@app.route('/')
@app.route('/teacher')
@app.route('/teacher.html')
def teacher_portal():
    return render_template('teacher.html')

@app.route('/student')
@app.route('/student.html')
def student_portal():
    return render_template('student.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)