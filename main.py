from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates

from pydantic import BaseModel
from typing import Dict
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import sessionmaker, declarative_base

from weasyprint import HTML
import io
import os

# ------------------------------------------------------------
# DATABASE SETUP
# ------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    room = Column(String)
    shift = Column(String)
    staff = Column(String)
    tasks_completed = Column(JSON)
    notes = Column(String, default="")
    timestamp = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)

# ------------------------------------------------------------
# FASTAPI APP
# ------------------------------------------------------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="app/app/templates")

# ------------------------------------------------------------
# REQUEST MODEL
# ------------------------------------------------------------

class SubmissionRequest(BaseModel):
    room: str
    shift: str
    staff: str
    tasks_completed: Dict[str, str]   # Y / N / NA
    notes: str = ""

# ------------------------------------------------------------
# SERIALIZER
# ------------------------------------------------------------

def serialize(entry):
    return {
        "id": entry.id,
        "room": entry.room,
        "shift": entry.shift,
        "staff": entry.staff,
        "tasks_completed": entry.tasks_completed,
        "notes": entry.notes,
        "timestamp": entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    }

# ------------------------------------------------------------
# ROUTES
# ------------------------------------------------------------

@app.post("/submit")
def submit_form(data: SubmissionRequest):
    db = SessionLocal()
    new_entry = Submission(
        room=data.room,
        shift=data.shift,
        staff=data.staff,
        tasks_completed=data.tasks_completed,
        notes=data.notes
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return {"message": "Submission saved", "id": new_entry.id}


@app.get("/submissions")
def get_submissions():
    db = SessionLocal()
    entries = db.query(Submission).order_by(Submission.timestamp.desc()).all()
    return [serialize(e) for e in entries]


@app.get("/all")
def get_all():
    db = SessionLocal()
    entries = db.query(Submission).all()
    return [serialize(e) for e in entries]


@app.head("/")
def head_check():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "Cleaning Survey API with PostgreSQL is running"}
    

from sqlalchemy import text

@app.get("/drop-submissions-table")
def drop_table():
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS submissions"))
    return {"status": "table dropped"}

# ------------------------------------------------------------
# PDF EXPORT
# ------------------------------------------------------------

@app.get("/export/pdf")
def export_pdf(request: Request):
    db = SessionLocal()
    submissions = db.query(Submission).all()

    total_submissions = len(submissions)

    if total_submissions > 0:
        avg_tasks = sum(len(s.tasks_completed) for s in submissions) / total_submissions
    else:
        avg_tasks = 0

    shift_counts = {}
    for s in submissions:
        shift_counts[s.shift] = shift_counts.get(s.shift, 0) + 1

    top_shift = max(shift_counts, key=shift_counts.get) if shift_counts else "N/A"

    overall_compliance = 92  # placeholder

    html_content = templates.get_template("dashboard_pdf.html").render({
        "overall_compliance": overall_compliance,
        "total_submissions": total_submissions,
        "top_shift": top_shift,
        "avg_tasks": round(avg_tasks, 2)
    })

    pdf_bytes = HTML(string=html_content).write_pdf()

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=cleaning_dashboard.pdf"}
    )
