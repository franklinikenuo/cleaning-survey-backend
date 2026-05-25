from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates

from pydantic import BaseModel
from typing import Dict
from datetime import datetime, timedelta
import csv
import io
import os
import datetime as dt

from sqlalchemy import Column, Integer, String, DateTime, JSON, text

from apscheduler.schedulers.background import BackgroundScheduler
from weasyprint import HTML

from database import engine, SessionLocal, Base
from cleanup.cleanup_old_records import cleanup_old_records
from cleanup.cleanup_logs import cleanup_logs

CLEANUP_TOKEN = os.getenv("CLEANUP_TOKEN")

# ------------------------------------------------------------
# MODELS
# ------------------------------------------------------------

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
    tasks_completed: Dict[str, str]
    notes: str = ""

# ------------------------------------------------------------
# SERIALIZER
# ------------------------------------------------------------

def serialize(entry: Submission):
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
    try:
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
    finally:
        db.close()


@app.get("/submissions")
def get_submissions():
    db = SessionLocal()
    try:
        entries = db.query(Submission).order_by(Submission.timestamp.desc()).all()
        return [serialize(e) for e in entries]
    finally:
        db.close()


@app.get("/all")
def get_all():
    db = SessionLocal()
    try:
        entries = db.query(Submission).all()
        return [serialize(e) for e in entries]
    finally:
        db.close()


@app.head("/")
def head_check():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "Cleaning Survey API with PostgreSQL is running"}

# ------------------------------------------------------------
# CSV EXPORT
# ------------------------------------------------------------

@app.get("/export-csv")
def export_csv():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM submissions"))
        rows = result.fetchall()
        headers = result.keys()

    def generate():
        yield ",".join(headers) + "\n"
        for row in rows:
            yield ",".join([str(x) for x in row]) + "\n"

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=submissions.csv"}
    )

# ------------------------------------------------------------
# DAILY ARCHIVE JOB
# ------------------------------------------------------------

def archive_daily():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM submissions"))
        rows = result.fetchall()
        headers = result.keys()

    filename = f"archive_{dt.date.today()}.csv"
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)

scheduler = BackgroundScheduler()
scheduler.add_job(archive_daily, "cron", hour=0, minute=0)
scheduler.start()

# ------------------------------------------------------------
# PDF EXPORT
# ------------------------------------------------------------

@app.get("/export/pdf")
def export_pdf(request: Request):
    db = SessionLocal()
    try:
        submissions = db.query(Submission).all()
    finally:
        db.close()

    total_submissions = len(submissions)
    avg_tasks = (
        sum(len(s.tasks_completed) for s in submissions) / total_submissions
        if total_submissions > 0 else 0
    )

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

# ------------------------------------------------------------
# CLEANUP ENDPOINTS
# ------------------------------------------------------------

def verify_token(request: Request):
    token = request.headers.get("X-Cleanup-Token")
    if token != CLEANUP_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/cleanup/status")
def cleanup_status():
    return {"status": "ok", "message": "Cleanup system installed"}


@app.get("/cleanup/run")
def cleanup_run(request: Request):
    verify_token(request)
    result = cleanup_old_records()
    return {"status": "success", "message": result}


@app.get("/cleanup/logs")
def cleanup_logs_route(request: Request):
    verify_token(request)
    result = cleanup_logs()
    return {"status": "success", "message": result}


# ------------------------------------------------------------
# WEEKLY / MONTHLY / QUARTERLY / YEARLY REPORTS
# ------------------------------------------------------------

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
REPORT_EMAIL = "franklin.ikenuo@gdi.com"


def generate_report_pdf(start_date, end_date):
    """Generate a PDF report for a given date range using the existing dashboard template."""
    db = SessionLocal()
    try:
        submissions = db.query(Submission).filter(
            Submission.timestamp >= start_date,
            Submission.timestamp <= end_date
        ).all()
    finally:
        db.close()

    total_submissions = len(submissions)
    avg_tasks = (
        sum(len(s.tasks_completed) for s in submissions) / total_submissions
        if total_submissions > 0 else 0
    )

    shift_counts = {}
    for s in submissions:
        shift_counts[s.shift] = shift_counts.get(s.shift, 0) + 1

    top_shift = max(shift_counts, key=shift_counts.get) if shift_counts else "N/A"

    overall_compliance = 92  # placeholder

    html_content = templates.get_template("dashboard_pdf.html").render({
        "overall_compliance": overall_compliance,
        "total_submissions": total_submissions,
        "top_shift": top_shift,
        "avg_tasks": round(avg_tasks, 2),
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d")
    })

    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes


def send_report_email(subject, pdf_bytes):
    """Send a PDF report via SendGrid."""
    message = Mail(
        from_email="no-reply@cleaning-survey.com",
        to_emails=REPORT_EMAIL,
        subject=subject,
        html_content=f"<p>Your report is attached.</p>"
    )

    encoded_pdf = base64.b64encode(pdf_bytes).decode()

    attachment = Attachment(
        FileContent(encoded_pdf),
        FileName("report.pdf"),
        FileType("application/pdf"),
        Disposition("attachment")
    )

    message.attachment = attachment

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        return "Email sent successfully"
    except Exception as e:
        return f"Error sending email: {str(e)}"


# ------------------------------------------------------------
# WEEKLY REPORT
# ------------------------------------------------------------
@app.get("/send-weekly-report")
def send_weekly_report():
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)

    pdf_bytes = generate_report_pdf(start_date, end_date)
    result = send_report_email("Weekly Cleaning Report", pdf_bytes)

    return {"status": "success", "message": result}


# ------------------------------------------------------------
# MONTHLY REPORT
# ------------------------------------------------------------
@app.get("/send-monthly-report")
def send_monthly_report():
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)

    pdf_bytes = generate_report_pdf(start_date, end_date)
    result = send_report_email("Monthly Cleaning Report", pdf_bytes)

    return {"status": "success", "message": result}


# ------------------------------------------------------------
# QUARTERLY REPORT
# ------------------------------------------------------------
@app.get("/send-quarterly-report")
def send_quarterly_report():
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=90)

    pdf_bytes = generate_report_pdf(start_date, end_date)
    result = send_report_email("Quarterly Cleaning Report", pdf_bytes)

    return {"status": "success", "message": result}


# ------------------------------------------------------------
# YEARLY REPORT
# ------------------------------------------------------------
@app.get("/send-yearly-report")
def send_yearly_report():
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=365)

    pdf_bytes = generate_report_pdf(start_date, end_date)
    result = send_report_email("Yearly Cleaning Report", pdf_bytes)

    return {"status": "success", "message": result}
