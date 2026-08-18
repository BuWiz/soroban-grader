from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models
from database import engine, get_db

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Root route - automatically redirects to teacher dashboard
@app.get("/")
def read_root():
    return RedirectResponse(url="/teacher")


@app.get("/teacher", response_class=HTMLResponse)
def teacher_dashboard(request: Request, db: Session = Depends(get_db)):
    worksheets = db.query(models.Worksheet).all()
    submissions = db.query(models.Submission).all()
    return templates.TemplateResponse(
        "teacher.html",
        {"request": request, "worksheets": worksheets, "submissions": submissions}
    )


@app.get("/student", response_class=HTMLResponse)
def student_portal(request: Request, db: Session = Depends(get_db)):
    worksheets = db.query(models.Worksheet).all()
    return templates.TemplateResponse(
        "student.html",
        {"request": request, "worksheets": worksheets}
    )


@app.get("/worksheet/{worksheet_id}", response_class=HTMLResponse)
def get_worksheet(worksheet_id: int, request: Request, db: Session = Depends(get_db)):
    worksheet = db.query(models.Worksheet).filter(models.Worksheet.id == worksheet_id).first()
    if not worksheet:
        raise HTTPException(status_code=404, detail="Worksheet not found")
    
    problems = db.query(models.Problem).filter(models.Problem.worksheet_id == worksheet_id).all()
    return templates.TemplateResponse(
        "worksheet.html",
        {"request": request, "worksheet": worksheet, "problems": problems}
    )


@app.post("/submit/{worksheet_id}", response_class=HTMLResponse)
async def submit_worksheet(
    worksheet_id: int,
    request: Request,
    student_name: str = Form(...),
    db: Session = Depends(get_db)
):
    form_data = await request.form()
    problems = db.query(models.Problem).filter(models.Problem.worksheet_id == worksheet_id).all()
    
    score = 0
    total = len(problems)
    
    for problem in problems:
        user_answer = form_data.get(f"problem_{problem.id}")
        if user_answer and str(user_answer).strip() == str(problem.answer).strip():
            score += 1
            
    submission = models.Submission(
        student_name=student_name,
        worksheet_id=worksheet_id,
        score=score,
        total=total
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    
    return templates.TemplateResponse(
        "results.html",
        {"request": request, "submission": submission}
    )