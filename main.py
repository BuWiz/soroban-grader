import json
import re
import secrets
import random
from datetime import datetime
from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from pypdf import PdfReader

from database import SessionLocal, Worksheet, Submission
from emailer import send_grade_email, save_teacher_email, get_teacher_email

app = FastAPI()
templates = Jinja2Templates(directory="templates")
security = HTTPBasic()

TEACHER_USERNAME = "admin"
TEACHER_PASSWORD = "sorobanpassword123"

def get_current_teacher(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, TEACHER_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, TEACHER_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

def generate_similar_problem(equation_str: str, digits: int = 1) -> dict:
    min_val = 10**(digits - 1) if digits > 1 else 1
    max_val = (10**digits) - 1

    a = random.randint(min_val, max_val)
    b = random.randint(min_val, max_val)

    if "-" in equation_str:
        if a < b:
            a, b = b, a
        eq = f"{a} - {b}"
        ans = float(a - b)
    elif "*" in equation_str or "x" in equation_str or "×" in equation_str:
        eq = f"{a} x {b}"
        ans = float(a * b)
    elif "/" in equation_str or "÷" in equation_str:
        ans_val = random.randint(1, 10)
        a = b * ans_val
        eq = f"{a} ÷ {b}"
        ans = float(ans_val)
    else:
        eq = f"{a} + {b}"
        ans = float(a + b)

    return {"equation": eq, "answer": ans}

# --- TEACHER DASHBOARD ---
@app.get("/teacher", response_class=HTMLResponse)
def teacher_dashboard(request: Request, username: str = Depends(get_current_teacher)):
    db = SessionLocal()
    worksheets = db.query(Worksheet).order_by(Worksheet.assigned_at.desc()).all()
    submissions = db.query(Submission).order_by(Submission.submitted_at.desc()).all()
    
    submission_logs = []
    for sub in submissions:
        ws = db.query(Worksheet).filter(Worksheet.id == sub.worksheet_id).first()
        submission_logs.append({
            "sub": sub,
            "worksheet_title": ws.title if ws else "Deleted Worksheet",
            "category": ws.category if ws else "N/A",
            "digits": ws.digits if ws else 1,
            "formatted_date": sub.submitted_at.strftime("%b %d, %Y at %I:%M %p") if sub.submitted_at else "N/A"
        })
        
    db.close()
    return templates.TemplateResponse(
        request=request, 
        name="teacher.html", 
        context={
            "worksheets": worksheets, 
            "submission_logs": submission_logs,
            "teacher_email": get_teacher_email()
        }
    )

@app.post("/teacher/save-email")
def update_email(email: str = Form(...), username: str = Depends(get_current_teacher)):
    save_teacher_email(email.strip())
    return RedirectResponse(url="/teacher", status_code=303)

@app.post("/teacher/create")
def create_worksheet(
    title: str = Form(...), 
    category: str = Form("Addition"), 
    digits: int = Form(1), 
    raw_problems: str = Form(...), 
    username: str = Depends(get_current_teacher)
):
    db = SessionLocal()
    lines = [line.strip() for line in raw_problems.strip().split("\n") if line.strip()]
    problems = []
    for line in lines:
        if "=" in line:
            eq, ans = line.split("=", 1)
            try:
                ans_val = float(ans.strip())
            except ValueError:
                ans_val = 0.0
            problems.append({"equation": eq.strip(), "answer": ans_val})
        else:
            clean_eq = line.strip()
            try:
                ans_val = float(eval(clean_eq.replace("x", "*").replace("÷", "/")))
            except Exception:
                ans_val = 0.0
            problems.append({"equation": clean_eq, "answer": ans_val})
    
    ws = Worksheet(title=title, category=category, digits=digits, is_flash=False, is_assigned=False, problems=problems)
    db.add(ws)
    db.commit()
    db.close()
    return RedirectResponse(url="/teacher", status_code=303)

@app.post("/teacher/create-flash")
def create_flash_worksheet(
    title: str = Form(...), 
    category: str = Form("Addition"), 
    digits: int = Form(1), 
    flash_speed_ms: int = Form(1500), 
    raw_sequences: str = Form(...), 
    username: str = Depends(get_current_teacher)
):
    db = SessionLocal()
    lines = [line.strip() for line in raw_sequences.strip().split("\n") if line.strip()]
    problems = []
    for line in lines:
        nums = [int(n.strip()) for n in line.split(",") if n.strip()]
        problems.append({"sequence": nums, "answer": float(sum(nums))})
        
    fws = Worksheet(title=title, category=category, digits=digits, is_flash=True, flash_speed_ms=flash_speed_ms, is_assigned=False, problems=problems)
    db.add(fws)
    db.commit()
    db.close()
    return RedirectResponse(url="/teacher", status_code=303)

# --- UPLOAD PDF (STANDARD OR FLASH ANZAN) ---
@app.post("/teacher/upload-pdf")
async def upload_pdf_worksheet(
    title: str = Form(...), 
    category: str = Form("Addition"), 
    digits: int = Form(1), 
    is_flash: bool = Form(False),
    flash_speed_ms: int = Form(1500),
    pdf_file: UploadFile = File(...), 
    username: str = Depends(get_current_teacher)
):
    contents = await pdf_file.read()
    reader = PdfReader(pdf_file.file)
    extracted_text = ""
    for page in reader.pages:
        extracted_text += page.extract_text() or ""

    lines = [line.strip() for line in extracted_text.split("\n") if line.strip()]
    problems = []

    if is_flash:
        # Extract sequences from PDF (e.g. "5, -3, 8" or "12 45 -10")
        for line in lines:
            nums = [int(n) for n in re.findall(r'-?\d+', line)]
            if len(nums) >= 2:
                problems.append({"sequence": nums, "answer": float(sum(nums))})
        if not problems:
            problems = [{"sequence": [5, 3, 2], "answer": 10.0}]
    else:
        # Extract standard equations
        for line in lines:
            if "=" in line:
                eq, ans = line.split("=", 1)
                try:
                    ans_val = float(ans.strip())
                except ValueError:
                    ans_val = 0.0
                problems.append({"equation": eq.strip(), "answer": ans_val})
            elif re.search(r'\d+\s*[\+\-\*x÷]\s*\d+', line):
                try:
                    ans_val = float(eval(line.replace("x", "*").replace("÷", "/")))
                except Exception:
                    ans_val = 0.0
                problems.append({"equation": line, "answer": ans_val})
        if not problems:
            problems = [{"equation": "1 + 1", "answer": 2.0}]

    db = SessionLocal()
    ws = Worksheet(
        title=title if title.strip() else pdf_file.filename.replace(".pdf", ""), 
        category=category, 
        digits=digits, 
        is_flash=is_flash,
        flash_speed_ms=flash_speed_ms,
        is_assigned=False, 
        problems=problems
    )
    db.add(ws)
    db.commit()
    db.close()
    return RedirectResponse(url="/teacher", status_code=303)

# --- ASSIGN / UNASSIGN ---
@app.post("/teacher/assign/{worksheet_id}")
def assign_worksheet(worksheet_id: int, username: str = Depends(get_current_teacher)):
    db = SessionLocal()
    ws = db.query(Worksheet).filter(Worksheet.id == worksheet_id).first()
    if ws:
        ws.is_assigned = True
        ws.assigned_at = datetime.utcnow()
        db.commit()
    db.close()
    return RedirectResponse(url="/teacher", status_code=303)

@app.post("/teacher/unassign/{worksheet_id}")
def unassign_worksheet(worksheet_id: int, username: str = Depends(get_current_teacher)):
    db = SessionLocal()
    ws = db.query(Worksheet).filter(Worksheet.id == worksheet_id).first()
    if ws:
        ws.is_assigned = False
        db.commit()
    db.close()
    return RedirectResponse(url="/teacher", status_code=303)

# --- 1-CLICK REMEDIAL GENERATOR ---
@app.post("/teacher/generate-remedial/{submission_id}")
def generate_remedial(submission_id: int, username: str = Depends(get_current_teacher)):
    db = SessionLocal()
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if sub and sub.incorrect_problems:
        orig_ws = db.query(Worksheet).filter(Worksheet.id == sub.worksheet_id).first()
        digits = orig_ws.digits if orig_ws else 1
        
        remedial_problems = []
        for item in sub.incorrect_problems:
            if orig_ws and orig_ws.is_flash:
                seq = item.get("sequence", [5, 3])
                remedial_problems.append({"sequence": seq, "answer": float(sum(seq))})
                new_seq = [random.randint(1, 9) for _ in range(len(seq))]
                remedial_problems.append({"sequence": new_seq, "answer": float(sum(new_seq))})
            else:
                eq_str = item.get("equation", "1 + 1")
                remedial_problems.append({"equation": eq_str, "answer": item.get("correct_answer")})
                remedial_problems.append(generate_similar_problem(eq_str, digits))
                remedial_problems.append(generate_similar_problem(eq_str, digits))

        remedial_title = f"Remedial Practice - {sub.student_name} ({orig_ws.title if orig_ws else 'Drill'})"
        remedial_ws = Worksheet(
            title=remedial_title, 
            category=orig_ws.category if orig_ws else "Mixed Operations", 
            digits=digits, 
            is_flash=orig_ws.is_flash if orig_ws else False,
            flash_speed_ms=orig_ws.flash_speed_ms if orig_ws else 1500,
            is_assigned=True,
            problems=remedial_problems
        )
        db.add(remedial_ws)
        db.commit()
    db.close()
    return RedirectResponse(url="/teacher", status_code=303)

# --- STUDENT PORTAL ---
@app.get("/student", response_class=HTMLResponse)
def student_portal(request: Request):
    db = SessionLocal()
    assigned_worksheets = db.query(Worksheet).filter(Worksheet.is_assigned == True).order_by(Worksheet.assigned_at.desc()).all()
    submissions = db.query(Submission).all()
    
    completed_ws_ids = {sub.worksheet_id for sub in submissions}
    
    due_worksheets = []
    completed_worksheets = []
    
    for ws in assigned_worksheets:
        if ws.id in completed_ws_ids:
            sub = next((s for s in submissions if s.worksheet_id == ws.id), None)
            completed_worksheets.append({
                "ws": ws,
                "score": sub.score if sub else 0.0,
                "formatted_date": sub.submitted_at.strftime("%b %d, %Y") if sub and sub.submitted_at else "Completed"
            })
        else:
            due_worksheets.append({
                "ws": ws,
                "formatted_assigned": ws.assigned_at.strftime("%b %d, %Y") if ws.assigned_at else "Today"
            })
            
    db.close()
    return templates.TemplateResponse(
        request=request, 
        name="student.html", 
        context={"due_worksheets": due_worksheets, "completed_worksheets": completed_worksheets}
    )

@app.get("/worksheet/{worksheet_id}", response_class=HTMLResponse)
def view_worksheet(request: Request, worksheet_id: int):
    db = SessionLocal()
    ws = db.query(Worksheet).filter(Worksheet.id == worksheet_id).first()
    db.close()
    if not ws:
        raise HTTPException(status_code=404, detail="Worksheet not found")
    
    template_name = "flash_worksheet.html" if ws.is_flash else "worksheet.html"
    return templates.TemplateResponse(request=request, name=template_name, context={"worksheet": ws})

# --- AUTOMATED GRADING & SUBMISSION (HANDLES BOTH STANDARD & FLASH ANZAN) ---
@app.post("/worksheet/{worksheet_id}/submit", response_class=HTMLResponse)
async def submit_worksheet(request: Request, worksheet_id: int, student_name: str = Form(...)):
    db = SessionLocal()
    ws = db.query(Worksheet).filter(Worksheet.id == worksheet_id).first()
    form_data = await request.form()

    incorrect_problems = []
    total_problems = len(ws.problems)
    correct_count = 0

    for idx, problem in enumerate(ws.problems):
        user_ans_str = form_data.get(f"answer_{idx}", "0")
        try:
            user_ans = float(user_ans_str)
        except ValueError:
            user_ans = 0.0

        expected_ans = float(problem.get("answer", 0.0))

        if abs(user_ans - expected_ans) < 0.01:
            correct_count += 1
        else:
            incorrect_problems.append({
                "equation": problem.get("equation", f"Sequence {idx+1}"),
                "sequence": problem.get("sequence", []),
                "user_answer": user_ans,
                "correct_answer": expected_ans
            })

    score = (correct_count / total_problems) * 100 if total_problems > 0 else 0.0

    submission = Submission(
        student_name=student_name,
        worksheet_id=worksheet_id,
        score=score,
        total_problems=total_problems,
        incorrect_problems=incorrect_problems,
        submitted_at=datetime.utcnow()
    )
    db.add(submission)
    db.commit()

    # Trigger Email Alert
    send_grade_email(
        student_name=student_name,
        worksheet_title=ws.title,
        score=score,
        total_problems=total_problems,
        incorrect_count=len(incorrect_problems)
    )

    db.refresh(submission)
    db.close()

    return templates.TemplateResponse(request=request, name="results.html", context={"submission": submission}) 