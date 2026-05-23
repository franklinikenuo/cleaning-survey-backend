from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates

from pydantic import BaseModel
from typing import Dict
from datetime import datetime
import csv
import io
import os
import datetime as dt

from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, text
from sqlalchemy.orm import sessionmaker, declarative_base

from apscheduler.schedulers.background import BackgroundScheduler
from weasyprint import HTML

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
# ------------------------------------------------------------
# WEEKLY REPORT ENDPOINT
# ------------------------------------------------------------

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64

@app.get("/send-weekly-report")
def send_weekly_report():
    db = SessionLocal()

    # Last 7 days
    week_start = datetime.utcnow() - timedelta(days=7)
    submissions = db.query(Submission).filter(Submission.timestamp >= week_start).all()

    total = len(submissions)

    # Compliance calculation
    def is_clean(task_dict):
        return all(v == "Y" for v in task_dict.values())

    clean_count = sum(1 for s in submissions if is_clean(s.tasks_completed))
    compliance = round((clean_count / total) * 100, 2) if total > 0 else 0

    # Build PDF HTML
    html_content = templates.get_template("dashboard_pdf.html").render({
        "overall_compliance": compliance,
        "total_submissions": total,
        "top_shift": "Weekly Summary",
        "avg_tasks": round(sum(len(s.tasks_completed) for s in submissions) / total, 2) if total else 0
    })

    pdf_bytes = HTML(string=html_content).write_pdf()

    # Encode PDF for email
    encoded_pdf = base64.b64encode(pdf_bytes).decode()

    message = Mail(
        from_email="no-reply@cleaning-survey.com",
        to_emails="franklin.ikenuo@gdi.com",
        subject="Weekly Cleaning Compliance Report",
        html_content=f"""
        <p>Hello Franklin,</p>
        <p>Your weekly cleaning compliance report is ready.</p>
        <p><strong>Total submissions:</strong> {total}</p>
        <p><strong>Compliance:</strong> {compliance}%</p>
        <p>The full PDF is attached.</p>
        """
    )

    attachment = Attachment(
        FileContent(encoded_pdf),
        FileName("weekly_report.pdf"),
        FileType("application/pdf"),
        Disposition("attachment")
    )

    message.attachment = attachment

    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        sg.send(message)
        return {"status": "Weekly report sent", "records": total}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
        
# ------------------------------------------------------------
# MONTHLY REPORT ENDPOINT
# ------------------------------------------------------------

@app.get("/send-monthly-report")
def send_monthly_report():
    db = SessionLocal()

    # Last 30 days
    month_start = datetime.utcnow() - timedelta(days=30)
    submissions = db.query(Submission).filter(Submission.timestamp >= month_start).all()

    total = len(submissions)

    # Compliance calculation
    def is_clean(task_dict):
        return all(v == "Y" for v in task_dict.values())

    clean_count = sum(1 for s in submissions if is_clean(s.tasks_completed))
    compliance = round((clean_count / total) * 100, 2) if total > 0 else 0

    # Build PDF HTML
    html_content = templates.get_template("dashboard_pdf.html").render({
        "overall_compliance": compliance,
        "total_submissions": total,
        "top_shift": "Monthly Summary",
        "avg_tasks": round(sum(len(s.tasks_completed) for s in submissions) / total, 2) if total else 0
    })

    pdf_bytes = HTML(string=html_content).write_pdf()

    # Encode PDF for email
    encoded_pdf = base64.b64encode(pdf_bytes).decode()

    message = Mail(
        from_email="no-reply@cleaning-survey.com",
        to_emails="franklin.ikenuo@gdi.com",
        subject="Monthly Cleaning Compliance Report",
        html_content=f"""
        <p>Hello Franklin,</p>
        <p>Your monthly cleaning compliance report is ready.</p>
        <p><strong>Total submissions:</strong> {total}</p>
        <p><strong>Compliance:</strong> {compliance}%</p>
        <p>The full PDF is attached.</p>
        """
    )

    attachment = Attachment(
        FileContent(encoded_pdf),
        FileName("monthly_report.pdf"),
        FileType("application/pdf"),
        Disposition("attachment")
    )

    message.attachment = attachment

    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        sg.send(message)
        return {"status": "Monthly report sent", "records": total}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# ------------------------------------------------------------
# QUARTERLY REPORT ENDPOINT
# ------------------------------------------------------------

@app.get("/send-quarterly-report")
def send_quarterly_report():
    db = SessionLocal()

    # Last 90 days
    quarter_start = datetime.utcnow() - timedelta(days=90)
    submissions = db.query(Submission).filter(Submission.timestamp >= quarter_start).all()

    total = len(submissions)

    # Compliance calculation
    def is_clean(task_dict):
        return all(v == "Y" for v in task_dict.values())

    clean_count = sum(1 for s in submissions if is_clean(s.tasks_completed))
    compliance = round((clean_count / total) * 100, 2) if total > 0 else 0

    # Build PDF HTML
    html_content = templates.get_template("dashboard_pdf.html").render({
        "overall_compliance": compliance,
        "total_submissions": total,
        "top_shift": "Quarterly Summary",
        "avg_tasks": round(sum(len(s.tasks_completed) for s in submissions) / total, 2) if total else 0
    })

    pdf_bytes = HTML(string=html_content).write_pdf()

    # Encode PDF for email
    encoded_pdf = base64.b64encode(pdf_bytes).decode()

    message = Mail(
        from_email="no-reply@cleaning-survey.com",
        to_emails="franklin.ikenuo@gdi.com",
        subject="Quarterly Cleaning Compliance Report",
        html_content=f"""
        <p>Hello Franklin,</p>
        <p>Your quarterly cleaning compliance report is ready.</p>
        <p><strong>Total submissions:</strong> {total}</p>
        <p><strong>Compliance:</strong> {compliance}%</p>
        <p>The full PDF is attached.</p>
        """
    )

    attachment = Attachment(
        FileContent(encoded_pdf),
        FileName("quarterly_report.pdf"),
        FileType("application/pdf"),
        Disposition("attachment")
    )

    message.attachment = attachment

    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        sg.send(message)
        return {"status": "Quarterly report sent", "records": total}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
# ------------------------------------------------------------
# YEARLY REPORT ENDPOINT
# ------------------------------------------------------------

@app.get("/send-yearly-report")
def send_yearly_report():
    db = SessionLocal()

    # Last 365 days
    year_start = datetime.utcnow() - timedelta(days=365)
    submissions = db.query(Submission).filter(Submission.timestamp >= year_start).all()

    total = len(submissions)

    # Compliance calculation
    def is_clean(task_dict):
        return all(v == "Y" for v in task_dict.values())

    clean_count = sum(1 for s in submissions if is_clean(s.tasks_completed))
    compliance = round((clean_count / total) * 100, 2) if total > 0 else 0

    # Build PDF HTML
    html_content = templates.get_template("dashboard_pdf.html").render({
        "overall_compliance": compliance,
        "total_submissions": total,
        "top_shift": "Yearly Summary",
        "avg_tasks": round(sum(len(s.tasks_completed) for s in submissions) / total, 2) if total else 0
    })

    pdf_bytes = HTML(string=html_content).write_pdf()

    # Encode PDF for email
    encoded_pdf = base64.b64encode(pdf_bytes).decode()

    message = Mail(
        from_email="no-reply@cleaning-survey.com",
        to_emails="franklin.ikenuo@gdi.com",
        subject="Yearly Cleaning Compliance Report",
        html_content=f"""
        <p>Hello Franklin,</p>
        <p>Your yearly cleaning compliance report is ready.</p>
        <p><strong>Total submissions:</strong> {total}</p>
        <p><strong>Compliance:</strong> {compliance}%</p>
        <p>The full PDF is attached.</p>
        """
    )

    attachment = Attachment(
        FileContent(encoded_pdf),
        FileName("yearly_report.pdf"),
        FileType("application/pdf"),
        Disposition("attachment")
    )

    message.attachment = attachment

    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        sg.send(message)
        return {"status": "Yearly report sent", "records": total}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
