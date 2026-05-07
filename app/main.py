from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, List
from datetime import datetime

from app.database import Base, engine, SessionLocal, Survey

app = FastAPI()

# Create tables on startup
Base.metadata.create_all(bind=engine)

# Pydantic model for incoming survey data
class SurveyRequest(BaseModel):
    room: str
    staff_name: str
    shift: str
    date: datetime
    tasks_completed: Dict[str, bool]
    notes: Optional[str] = None

@app.get("/")
def root():
    return {"message": "Cleaning Survey API is running"}

@app.post("/survey")
def submit_survey(data: SurveyRequest):
    db = SessionLocal()
    survey = Survey(**data.dict())
    db.add(survey)
    db.commit()
    db.refresh(survey)
    return {"status": "success", "id": survey.id}

@app.get("/survey")
def get_all_surveys():
    db = SessionLocal()
    return db.query(Survey).all()

@app.get("/survey/{survey_id}")
def get_survey(survey_id: int):
    db = SessionLocal()
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    return survey
