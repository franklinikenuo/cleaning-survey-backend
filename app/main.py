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
    try:
        surveys = requests.get(SURVEY_API).json()
    except Exception as e:
        return {"error": f"Failed to fetch survey data: {e}"}

    # Ensure surveys is ALWAYS a list
    if isinstance(surveys, dict):
        surveys = [surveys]

    if not surveys:
        return {"error": "No survey data returned from API"}

    df = pd.DataFrame(surveys)

    # Validate required fields
    required = ["date", "tasks_completed"]
    for col in required:
        if col not in df.columns:
            return {"error": f"Survey data missing required field: {col}"}

    # Convert date column
    try:
        df["date"] = pd.to_datetime(df["date"])
    except:
        return {"error": "Invalid date format in survey data"}

    # ============================
    # 2. Filter to current week
    # ============================
    today = pd.Timestamp.today().normalize()
    week_start = today - pd.Timedelta(days=today.weekday())  # Monday

    weekly = df[df["date"] >= week_start]

    # ============================
    # 3. Compute compliance
    # ============================
    def is_clean(task_dict):
        if not isinstance(task_dict, dict):
            return False
        return all(task_dict.values())

    if len(weekly) == 0:
        compliance = 0
    else:
        weekly["clean"] = weekly["tasks_completed"].apply(is_clean)
        compliance = round((weekly["clean"].sum() / len(weekly)) * 100, 2)

    # ============================
    # 4. Generate chart
    # ============================
    plt.figure(figsize=(8, 4))
    plt.bar(["Compliance"], [compliance], color="green" if compliance >= 80 else "red")
    plt.ylim(0, 100)
    plt.title("Weekly Cleaning Compliance (%)")
    plt.ylabel("Percentage")

    chart_buffer = BytesIO()
    plt.savefig(chart_buffer, format="png")
    chart_buffer.seek(0)
    plt.close()

    # ============================
    # 5. Build PDF
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
    # 6. Email PDF
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

    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        sg.send(message)
    except Exception as e:
        return {"error": f"Failed to send email: {e}"}

    return {
        "status": "Weekly report sent",
        "compliance": compliance,
        "records_this_week": len(weekly)
    }
