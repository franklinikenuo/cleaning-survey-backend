from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional

app = FastAPI()

# Allow your GitHub Pages form + dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # you can restrict later
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory store (resets on deploy)
DB: List[Dict] = []


class Survey(BaseModel):
    room: str
    staff_name: str
    shift: str
    date: str
    tasks_completed: Dict[str, bool]
    notes: Optional[str] = None


@app.get("/")
def root():
    return {"status": "API running"}


@app.get("/survey")
def get_surveys():
    return DB


@app.post("/survey")
def create_survey(survey: Survey):
    entry = survey.dict()
    entry["id"] = len(DB) + 1
    DB.append(entry)
    return {"message": "Survey saved", "id": entry["id"]}
