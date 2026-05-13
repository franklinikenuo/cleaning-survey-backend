from fastapi import FastAPI, HTTPException,  Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, JSON, TIMESTAMP, text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import os

# -----------------------------
# Database Setup
# -----------------------------
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL is not set in environment variables")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# -----------------------------
# Database Model
# -----------------------------
class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    room = Column(String)
    staff_name = Column(String)
    shift = Column(String)
    tasks_completed = Column(JSON)
    notes = Column(String)
    timestamp = Column(TIMESTAMP, server_default=text("NOW()"))

# Create table if not exists
Base.metadata.create_all(bind=engine)

# -----------------------------
# FastAPI Setup
# -----------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Request Model
# -----------------------------
class SubmissionRequest(BaseModel):
    room: str
    staff_name: str
    shift: str
    tasks_completed: dict
    notes: str | None = None

# -----------------------------
# Routes
# -----------------------------
@app.post("/submit")
def submit_data(data: SubmissionRequest):
    db = SessionLocal()
    try:
        new_entry = Submission(
            room=data.room,
            staff_name=data.staff_name,
            shift=data.shift,
            tasks_completed=data.tasks_completed,
            notes=data.notes
        )
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)
        return {"status": "success", "id": new_entry.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/submissions")
def get_submissions():
    db = SessionLocal()
    try:
        entries = db.query(Submission).order_by(Submission.timestamp.desc()).all()
        return entries
    finally:
        db.close()
        
        from fastapi import Response
@app.head("/submissions")
def head_submissions():
    return Response(status_code=200)


@app.get("/")
def root():
    return {"message": "Cleaning Survey API with PostgreSQL is running"}
