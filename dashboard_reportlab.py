from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch


def generate_dashboard_pdf(filepath, overall_compliance, total_submissions, top_shift, avg_tasks):
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter

    # ================================
    # COLORS (Clinical Premium Theme)
    # ================================
    PRIMARY = colors.HexColor("#0f3d91")
    PRIMARY_LIGHT = colors.HexColor("#e3edff")
    TEXT_MAIN = colors.HexColor("#1a2b49")
    TEXT_MUTED = colors.HexColor("#6b7a99")
    BORDER = colors.HexColor("#d6e2fb")

    # ================================
    # HEADER
    # ================================
    c.setFillColor(PRIMARY)
    c.rect(0, height - 90, width, 90, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(40, height - 50, "Cleaning Compliance Dashboard Report")

    c.setFont("Helvetica", 12)
    c.drawString(40, height - 70, "Automated Compliance Summary")

    # ================================
    # SECTION TITLE
    # ================================
    c.setFillColor(TEXT_MAIN)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height - 130, "Key Performance Indicators")

    # ================================
    # KPI BOXES
    # ================================
    box_y = height - 260
    box_width = (width - 100) / 2
    box_height = 90

    kpis = [
        ("Overall Compliance", f"{overall_compliance}%", PRIMARY),
        ("Total Submissions", str(total_submissions), colors.HexColor("#1abc9c")),
        ("Top Shift", top_shift, colors.HexColor("#0f3d91")),
        ("Avg Tasks Completed", str(avg_tasks), colors.HexColor("#6b7a99")),
    ]

    for i, (title, value, color) in enumerate(kpis):
        col = i % 2
        row = i // 2

        x = 40 + col * (box_width + 20)
        y = box_y - (row * (box_height + 20))

        # Box background
        c.setFillColor(PRIMARY_LIGHT)
        c.roundRect(x, y, box_width, box_height, 10, fill=1, stroke=0)

        # Border
        c.setStrokeColor(BORDER)
        c.roundRect(x, y, box_width, box_height, 10, fill=0, stroke=1)

        # Title
        c.setFillColor(TEXT_MUTED)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x + 14, y + box_height - 28, title)

        # Value
        c.setFillColor(color)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(x + 14, y + box_height - 58, value)

    # ================================
    # FOOTER
    # ================================
    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, 30, "Generated automatically by Cleaning Compliance System")

    c.showPage()
    c.save()
