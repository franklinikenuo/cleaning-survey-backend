from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import matplotlib.pyplot as plt
import pandas as pd
import base64
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os
import requests

app = FastAPI()

# Allow dashboard to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SURVEY_API = "https://cleaning-survey-api.onrender.com/survey"


@app.get("/")
def root():
    return {"status": "Backend running"}


@app.get("/send-weekly-report")
def send_weekly_report():
    # ============================
    # 1. Fetch survey data
    # ============================
    surveys = requests.get(SURVEY_API).json()

    df = pd.DataFrame([surveys])
    df['date'] = pd.to_datetime(df['date'])

    # Start of week (Monday)
    week_start = pd.Timestamp.today().normalize() - pd.Timedelta(days=pd.Timestamp.today().weekday())
    weekly = df[df['date'] >= week_start]

    # ============================
    # 2. Compute compliance
    # ============================
    def is_clean(task_dict):
        return all(task_dict.values())

    weekly['clean'] = weekly['tasks_completed'].apply(is_clean)

    compliance = round((weekly['clean'].sum() / len(weekly)) * 100, 2) if len(weekly) else 0

    # ============================
    # 3. Generate chart
    # ============================
    plt.figure(figsize=(8, 4))
    weekly.groupby("room")['clean'].mean().plot(kind='bar', color='teal')
    plt.title("Weekly Room Compliance")
    plt.ylabel("Compliance %")
    plt.tight_layout()

    chart_buffer = BytesIO()
    plt.savefig(chart_buffer, format='png')
    chart_buffer.seek(0)

    # ============================
    # 4. Build PDF
    # ============================
    pdf_buffer = BytesIO()
    pdf = canvas.Canvas(pdf_buffer, pagesize=letter)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, 750, "Weekly Cleaning Report")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, 730, f"Compliance: {compliance}%")
    pdf.drawString(50, 715, f"Total Submissions: {len(weekly)}")

    # Insert chart
    pdf.drawImage(chart_buffer, 50, 450, width=500, height=250)

    pdf.showPage()
    pdf.save()
    pdf_buffer.seek(0)

    # ============================
    # 5. Email PDF
    # ============================
    encoded_pdf = base64.b64encode(pdf_buffer.read()).decode()

    message = Mail(
        from_email="no-reply@cleaning-system.com",
        to_emails="YOUR_EMAIL@domain.com",
        subject="Weekly Cleaning Report",
        html_content="Attached is your weekly cleaning report."
    )

    attachment = Attachment(
        FileContent(encoded_pdf),
        FileName("weekly_report.pdf"),
        FileType("application/pdf"),
        Disposition("attachment")
    )

    message.attachment = attachment

    sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
    sg.send(message)

    return {"status": "Weekly report sent"}
