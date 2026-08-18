from sqlalchemy import create_engine, Column, Integer, String, Float, JSON, ForeignKey, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./grader.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Worksheet(Base):
    __tablename__ = "worksheets"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    category = Column(String, default="Addition")  # Addition, Subtraction, Multiplication, Division
    digits = Column(Integer, default=1)           # 1-Digit, 2-Digit, 3-Digit, 4-Digit
    is_flash = Column(Boolean, default=False)
    flash_speed_ms = Column(Integer, default=1500)
    is_assigned = Column(Boolean, default=False)
    problems = Column(JSON)
    assigned_at = Column(DateTime, default=datetime.utcnow)

class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String)
    worksheet_id = Column(Integer, ForeignKey("worksheets.id"))
    score = Column(Float)
    total_problems = Column(Integer)
    incorrect_problems = Column(JSON)
    submitted_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine) 