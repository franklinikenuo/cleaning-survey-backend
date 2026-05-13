from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import os
from fpdf import FPDF
import sendgrid
from sendgrid.helpers.mail import Mail

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "submissions.json"

# Ensure file exists
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump([], f)


# -----------------------------
# MODELS
# -----------------------------
class Tasks(BaseModel):
    floor_cleaned: bool
    trash_removed: bool
    surfaces_wiped: bool
    equipment_sanitized: bool
    supplies_restocked: bool
    swept: bool
    linen_change: bool
    vacuum: bool


class Submission(BaseModel):
    room: str
    staff_name: str
    shift: str
    tasks_completed: Tasks
    notes: str = ""


# -----------------------------
# ROOT (HEALTH CHECK)
# -----------------------------
@app.get("/")
def root():
    return {"status": "Backend running"}


# -----------------------------
# SUBMIT CLEANING SURVEY
# -----------------------------
@app.post("/submit")
def submit_survey(submission: Submission):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    entry = submission.dict()
    entry["timestamp"] = datetime.now().isoformat()

    data.append(entry)

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

    return {"message": "Submission saved", "data": entry}


# -----------------------------
# GET ALL SUBMISSIONS
# -----------------------------
@app.get("/submissions")
def get_submissions():
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    return data


# ⭐ NEW — HEAD ROUTE FOR UPTIMEROBOT
@app.head("/submissions")
def submissions_head():
    return {"status": "Backend running"}


# -----------------------------
# GET ALL (ALIAS)
# -----------------------------
@app.get("/all")
def get_all():
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    return data


# -----------------------------
# PDF GENERATION
# -----------------------------
def generate_pdf_report(title, entries):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt=title, ln=True, align="C")
    pdf.ln(5)

    for entry in entries:
        pdf.multi_cell(0, 8, txt=f"Room: {entry['room']}")
        pdf.multi_cell(0, 8, txt=f"Staff: {entry['staff_name']}")
        pdf.multi_cell(0, 8, txt=f"Shift: {entry['shift']}")
        pdf.multi_cell(0, 8, txt=f"Timestamp: {entry['timestamp']}")
        pdf.multi_cell(0, 8, txt=f"Tasks: {entry['tasks_completed']}")
        pdf.multi_cell(0, 8, txt=f"Notes: {entry['notes']}")
        pdf.ln(5)

    filename = f"{title.replace(' ', '_')}.pdf"
    pdf.output(filename)
    return filename


# -----------------------------
# WEEKLY REPORT
# -----------------------------
@app.get("/weekly-report")
def weekly_report():
    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    one_week_ago = datetime.now() - timedelta(days=7)
    filtered = [d for d in data if datetime.fromisoformat(d["timestamp"]) >= one_week_ago]

    if not filtered:
        raise HTTPException(status_code=404, detail="No submissions in the last week")

    filename = generate_pdf_report("Weekly Report", filtered)
    return {"message": "Weekly report generated", "file": filename}


# -----------------------------
# MONTHLY REPORT
# -----------------------------
@app.get("/monthly-report")
def monthly_report():
    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    one_month_ago = datetime.now() - timedelta(days=30)
    filtered = [d for d in data if datetime.fromisoformat(d["timestamp"]) >= one_month_ago]

    if not filtered:
        raise HTTPException(status_code=404, detail="No submissions in the last month")

    filename = generate_pdf_report("Monthly Report", filtered)
    return {"message": "Monthly report generated", "file": filename}


# -----------------------------
# SENDGRID EMAIL (OPTIONAL)
# -----------------------------
@app.post("/send-report")
def send_report(email: str, report_type: str):
    sg = sendgrid.SendGridAPIClient(api_key=os.getenv("SENDGRID_API_KEY"))

    filename = f"{report_type}.pdf"
    if not os.path.exists(filename):
        raise HTTPException(status_code=404, detail="Report not found")

    message = Mail(
        from_email="noreply@cleaning-survey.com",
        to_emails=email,
        subject=f"{report_type} Report",
        html_content=f"Attached is your {report_type} report."
    )

    with open(filename, "rb") as f:
        message.add_attachment(
            f.read(),
            "application/pdf",
            filename
        )

    sg.send(message)
    return {"message": "Email sent"}
