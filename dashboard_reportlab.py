from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch

def generate_dashboard_pdf(filepath, overall_compliance, total_submissions, top_shift, avg_tasks):
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 60, "Cleaning Compliance Dashboard")

    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, height - 80, "Generated PDF Report")

    # KPI Section Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height - 130, "Key Performance Indicators")

    # KPI Boxes
    box_y = height - 180
    box_width = (width - 80) / 4
    box_height = 80

    kpis = [
        ("Overall Compliance", f"{overall_compliance}%"),
        ("Total Submissions", str(total_submissions)),
        ("Top Shift", top_shift),
        ("Avg Tasks Completed", str(avg_tasks)),
    ]

    for i, (title, value) in enumerate(kpis):
        x = 40 + i * box_width

        # Box background
        c.setFillColor(colors.whitesmoke)
        c.rect(x, box_y, box_width - 10, box_height, fill=1, stroke=0)

        # Border
        c.setStrokeColor(colors.lightgrey)
        c.rect(x, box_y, box_width - 10, box_height, fill=0, stroke=1)

        # Text
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x + 10, box_y + box_height - 25, title)

        c.setFont("Helvetica", 14)
        c.drawString(x + 10, box_y + box_height - 50, value)

    c.showPage()
    c.save()
