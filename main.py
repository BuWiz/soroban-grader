@app.route('/')
def home():
    # Set student.html (or teacher.html) as your main home page
    return render_template('student.html')

@app.route('/teacher')
def teacher():
    return render_template('teacher.html')

@app.route('/worksheet')
def worksheet():
    return render_template('worksheet.html')

@app.route('/results')
def results():
    return render_template('results.html')