import os
import sys

# 1. Force the root folder onto Python's module path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from fastapi import FastAPI, Depends, Form, File, UploadFile, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import pypdf

# 2. Configure SQLite in Vercel's temporary writable /tmp directory
DATABASE_URL = "sqlite:////tmp/soroban.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 3. Models Setup
class Worksheet(Base):
    __tablename__ = "worksheets"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    operation = Column(String)
    digits = Column(String)
    problems = Column(Text)
    is_pdf = Column(Boolean, default=False)
    is_flash = Column(Boolean, default=False)
    flash_speed = Column(Integer, default=3)

class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String)
    worksheet_id = Column(Integer)
    score = Column(Integer)
    total = Column(Integer)

Base.metadata.create_all(bind=engine)

# 4. FastAPI App Setup
app = FastAPI(title="Soroban Grader")

# Absolute path resolution for templates on Vercel
templates_dir = os.path.join(root_dir, "templates")
templates = Jinja2Templates(directory=templates_dir)

static_dir = os.path.join(root_dir, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 5. Application Routes
@app.get("/", response_class=HTMLResponse)
@app.get("/student", response_class=HTMLResponse)
async def student_portal(request: Request, db: Session = Depends(get_db)):
    worksheets = db.query(Worksheet).all()
    sanitized = [
        {
            "id": ws.id,
            "title": ws.title,
            "operation": ws.operation,
            "digits": ws.digits,
            "is_flash": ws.is_flash,
            "flash_speed": ws.flash_speed
        }
        for ws in worksheets
    ]
    return templates.TemplateResponse("student.html", {"request": request, "worksheets": sanitized})

@app.get("/teacher", response_class=HTMLResponse)
async def teacher_dashboard(request: Request, db: Session = Depends(get_db)):
    standards = db.query(Worksheet).all()
    return templates.TemplateResponse("teacher.html", {"request": request, "standards": standards})

@app.post("/create-standard")
async def create_standard(
    title: str = Form(...),
    operation: str = Form(...),
    digits: str = Form(...),
    problems: str = Form(...),
    db: Session = Depends(get_db)
):
    ws = Worksheet(title=title, operation=operation, digits=digits, problems=problems, is_pdf=False)
    db.add(ws)
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
    extracted_text = "".join([page.extract_text() + "\n" for page in pdf_reader.pages])
    ws = Worksheet(title=title, operation=operation, digits=digits, problems=extracted_text, is_pdf=True)
    db.add(ws)
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
    ws = Worksheet(title=title, operation=operation, digits=digits, problems=sequences, is_flash=True, flash_speed=speed)
    db.add(ws)
    db.commit()
    return RedirectResponse(url="/teacher", status_code=303)

@app.post("/submit")
async def submit_worksheet(
    student_name: str = Form(...),
    worksheet_id: int = Form(...),
    score: int = Form(...),
    total: int = Form(...),
    db: Session = Depends(get_db)
):
    sub = Submission(student_name=student_name, worksheet_id=worksheet_id, score=score, total=total)
    db.add(sub)
    db.commit()
    return JSONResponse({"status": "success", "submission_id": sub.id})