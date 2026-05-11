from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import datetime
import json
import os

app = FastAPI()

# Allow dashboard + survey to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================
# STORAGE FILE
# ============================
DATA_FILE = "submissions.json"

# Create file if missing
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump([], f, indent=2)


# ============================
# STRICT DATA MODELS
# ============================

class Tasks(BaseModel):
    floor_cleaned: bool = False
    trash_removed: bool = False
    surfaces_wiped: bool = False
    equipment_sanitized: bool = False
    supplies_restocked: bool = False
    sweep: bool = False
    linen_change: bool = False
    vacuum: bool = False

class SurveyData(BaseModel):
    room: str = Field(..., min_length=1)
    staff_name: str = Field(..., min_length=1)
    shift: str = Field(..., regex="^(Morning|Evening|Night)$")
    tasks_completed: Tasks
    notes: Optional[str] = ""


# ============================
# STORAGE HELPERS
# ============================

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ============================
# HEALTH CHECK
# ============================
@app.get("/")
def root():
    return {"status": "Backend running"}


# ============================
# SUBMIT SURVEY
# ============================
@app.post("/submit")
async def submit_survey(data: SurveyData):
    submissions = load_data()

    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "room": data.room,
        "staff_name": data.staff_name,
        "shift": data.shift,
        "tasks_completed": data.tasks_completed.dict(),
        "notes": data.notes or ""
    }

    submissions.append(entry)
    save_data(submissions)

    return {"status": "success", "message": "Survey saved", "entry": entry}


# ============================
# GET ALL SUBMISSIONS
# ============================
@app.get("/submissions")
async def get_submissions():
    return load_data()


# ============================
# WEEKLY REPORT (placeholder)
# ============================
@app.get("/send-weekly-report")
async def weekly_report():
    return {"status": "ok", "message": "Weekly report endpoint ready"}


# ============================
# MONTHLY REPORT (placeholder)
# ============================
@app.get("/send-monthly-report")
async def monthly_report():
    return {"status": "ok", "message": "Monthly report endpoint ready"}
