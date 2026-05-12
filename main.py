from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import datetime
import json
import os

# PDF generation
from fpdf import FPDF

# Email (SendGrid)
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileName, FileType, Disposition

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
    shift: str = Field(..., pattern="^(Morning|Evening|Night)$")
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
# GET ALL (dashboard endpoint)
# ============================
@app.get("/all")
async def get_all():
    return load_data()


# ============================
# PDF GENERATOR
# ============================
def generate_weekly_pdf(submissions):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Weekly Cleaning Report", ln=True, align="C")
    pdf.ln(5)

    if not submissions:
        pdf.cell(200, 10, txt="No submissions this week.", ln=True)
    else:
        for s in submissions:
            pdf.cell(200, 8, txt=f"Room: {s['room']}", ln=True)
            pdf.cell(200, 8, txt=f"Staff: {s['staff_name']}", ln=True)
            pdf.cell(200, 8, txt=f"Shift: {s['shift']}", ln=True)
            pdf.cell(200, 8, txt=f"Timestamp: {s['timestamp']}", ln=True)
            pdf.ln(4)

    filename = "weekly_report.pdf"
    pdf.output(filename)
    return filename


# ============================
# WEEKLY REPORT WITH PDF EMAIL
# ============================
@app.get("/send-weekly-report")
async def send_weekly_report():
    try:
        submissions = load_data()
        pdf_file = generate_weekly_pdf(submissions)

        # Read PDF for attachment
        with open(pdf_file, "rb") as f:
            pdf_data = f.read()

        encoded_pdf = pdf_data.encode("base64") if hasattr(pdf_data, "encode") else pdf_data

        sg = sendgrid.SendGridAPIClient(api_key=os.getenv("SENDGRID_API_KEY"))

        from_email = Email("franklin.ikenuo@gdi.com")
        to_email = To("franklin.ikenuo@gdi.com")
        subject = "Weekly Cleaning Report (PDF Attached)"
        content = Content("text/plain", "Your weekly cleaning report is attached.")

        attachment = Attachment()
        attachment.file_content = FileContent(pdf_data)
        attachment.file_type = FileType("application/pdf")
        attachment.file_name = FileName("weekly_report.pdf")
        attachment.disposition = Disposition("attachment")

        mail = Mail(from_email, to_email, subject, content)
        mail.attachment = attachment

        response = sg.client.mail.send.post(request_body=mail.get())

        return {
            "status": "sent",
            "code": response.status_code,
            "message": "Weekly report email with PDF sent successfully"
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================
# MONTHLY REPORT (placeholder)
# ============================
@app.get("/send-monthly-report")
async def monthly_report():
    return {"status": "ok", "message": "Monthly report endpoint ready"}
