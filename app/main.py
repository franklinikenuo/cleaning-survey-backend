from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from fpdf import FPDF
from datetime import datetime, timedelta
import base64
import json
import os

app = FastAPI()

# Allow dashboard to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SURVEY_FILE = "surveys.json"

# Ensure survey storage file exists
if not os.path.exists(SURVEY_FILE):
    with open(SURVEY_FILE, "w") as f:
        json.dump([], f)


# ============================
# 0. Health Check
# ============================
@app.get("/")
def root():
    return {"status": "Backend running"}


# ============================
# 1. Submit Survey
# ============================
@app.post("/survey")
def submit_survey(survey: dict):
    survey["date"] = datetime.utcnow().isoformat()

    with open(SURVEY_FILE, "r") as f:
        data = json.load(f)

    data.append(survey)

    with open(SURVEY_FILE, "w") as f:
        json.dump(data, f)

    return {"status": "Survey saved", "survey": survey}


# ============================
# 2. Get All Surveys
# ============================
@app.get("/survey")
def get_surveys():
    with open(SURVEY_FILE, "r") as f:
        data = json.load(f)
    return data


# ============================
# Helper: Load surveys safely
# ============================
def load_surveys():
    try:
        with open(SURVEY_FILE, "r") as f:
            return json.load(f)
    except:
        return []


# ============================
# Helper: Filter surveys by days
# ============================
def filter_surveys(days: int):
    surveys = load_surveys()
    cutoff = datetime.utcnow() - timedelta(days=days)

    filtered = []
    for s in surveys:
        try:
            date = datetime.fromisoformat(s["date"])
            if date >= cutoff:
                filtered.append(s)
        except:
            continue

    return filtered


# ============================
# Helper: Generate PDF
# ============================
def generate_pdf(title: str, surveys: list, filename: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)

    pdf.cell(200, 10, txt=title, ln=True, align="C")
    pdf.ln(5)

    if not surveys:
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="No survey data available.", ln=True)
    else:
        for s in surveys:
            clean = all(s["tasks_completed"].values())
            line = f"{s['room']} - {'Clean' if clean else 'Not Clean'} - {s['date']}"
            pdf.set_font("Arial", size=11)
            pdf.cell(200, 8, txt=line, ln=True)

    pdf.output(filename)
    return filename


# ============================
# Helper: Email PDF
# ============================
def email_pdf(filename: str, subject: str, message_text: str):
    with open(filename, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    message = Mail(
        from_email="franklin.ikenuo@gdi.com",
        to_emails="YOUR_EMAIL@domain.com",
        subject=subject,
        html_content=message_text
    )

    attachment = Attachment(
        FileContent(encoded),
        FileName(filename),
        FileType("application/pdf"),
        Disposition("attachment")
    )

    message.attachment = attachment

    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        sg.send(message)
        return True
    except Exception as e:
        return str(e)


# ============================
# 3. Weekly Report
# ============================
@app.get("/send-weekly-report")
def send_weekly_report():
    weekly = filter_surveys(7)
    filename = "weekly_report.pdf"

    generate_pdf("Weekly Cleaning Report", weekly, filename)

    result = email_pdf(filename, "Weekly Cleaning Report", "Attached is your weekly cleaning report.")

    if result is True:
        return {"status": "Weekly report sent", "records": len(weekly)}
    else:
        return {"error": result}


# ============================
# 4. Monthly Report
# ============================
@app.get("/send-monthly-report")
def send_monthly_report():
    monthly = filter_surveys(30)
    filename = "monthly_report.pdf"

    generate_pdf("Monthly Cleaning Report", monthly, filename)

    result = email_pdf(filename, "Monthly Cleaning Report", "Attached is your monthly cleaning report.")

    if result is True:
        return {"status": "Monthly report sent", "records": len(monthly)}
    else:
        return {"error": result}
