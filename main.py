import os
from fastapi import FastAPI, Depends, Form, File, UploadFile, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import pypdf

import database
import models

app = FastAPI(title="Soroban Grader")

# Ensure database tables are created on startup
@app.on_event("startup")
def startup():
    models.Base.metadata.create_all(bind=database.engine)

# Static files and Template setup
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================================
# ROOT REDIRECT
# ==========================================
@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/student")


# ==========================================
# TEACHER PORTAL & CREATION ROUTES
# ==========================================
@app.get("/teacher", response_class=HTMLResponse)
async def teacher_dashboard(request: Request, db: Session = Depends(get_db)):
    standards = db.query(models.Worksheet).all()
    return templates.TemplateResponse(
        "teacher.html", 
        {"request": request, "standards": standards}
    )

@app.post("/create-standard")
async def create_standard(
    title: str = Form(...),
    operation: str = Form(...),
    digits: str = Form(...),
    problems: str = Form(...),
    db: Session = Depends(get_db)
):
    worksheet = models.Worksheet(
        title=title,
        operation=operation,
        digits=digits,
        problems=problems,
        is_pdf=False
    )
    db.add(worksheet)
    db.commit()
    return RedirectResponse(url="/teacher", status_code=303)

@app.post("/upload-pdf")
async def upload_pdf(
    title: str = Form(...),
    operation: str = Form(...),
    digits: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    pdf_reader = pypdf.PdfReader(file.file)
    extracted_text = ""
    for page in pdf_reader.pages:
        extracted_text += page.extract_text() + "\n"

    worksheet = models.Worksheet(
        title=title,
        operation=operation,
        digits=digits,
        problems=extracted_text,
        is_pdf=True
    )
    db.add(worksheet)
    db.commit()
    return RedirectResponse(url="/teacher", status_code=303)

@app.post("/create-flash")
async def create_flash(
    title: str = Form(...),
    operation: str = Form(...),
    digits: str = Form(...),
    speed: int = Form(...),
    sequences: str = Form(...),
    db: Session = Depends(get_db)
):
    worksheet = models.Worksheet(
        title=title,
        operation=operation,
        digits=digits,
        problems=sequences,
        is_flash=True,
        flash_speed=speed
    )
    db.add(worksheet)
    db.commit()
    return RedirectResponse(url="/teacher", status_code=303)


# ==========================================
# STUDENT PORTAL & SUBMISSION ROUTES
# ==========================================
@app.get("/student", response_class=HTMLResponse)
async def student_portal(request: Request, db: Session = Depends(get_db)):
    worksheets = db.query(models.Worksheet).all()
    
    sanitized_worksheets = []
    for ws in worksheets:
        sanitized_worksheets.append({
            "id": ws.id,
            "title": ws.title,
            "operation": ws.operation,
            "digits": ws.digits,
            "is_flash": ws.is_flash,
            "flash_speed": ws.flash_speed
        })
        
    return templates.TemplateResponse(
        "student.html", 
        {"request": request, "worksheets": sanitized_worksheets}
    )

@app.post("/submit")
async def submit_worksheet(
    student_name: str = Form(...),
    worksheet_id: int = Form(...),
    score: int = Form(...),
    total: int = Form(...),
    db: Session = Depends(get_db)
):
    submission = models.Submission(
        student_name=student_name,
        worksheet_id=worksheet_id,
        score=score,
        total=total
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return JSONResponse({"status": "success", "submission_id": submission.id})