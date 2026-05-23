from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from cleanup.utils import ensure_dir

def export_to_pdf(records, filepath):
    ensure_dir(filepath.rsplit("/", 1)[0])

    c = canvas.Canvas(filepath, pagesize=letter)
    y = 750

    c.setFont("Helvetica-Bold", 14)
    c.drawString(30, y, "Archived Cleaning Submissions")
    y -= 30

    c.setFont("Helvetica", 10)

    for r in records:
        line = f"{r['timestamp']} | {r['room']} | {r['staff']} | {r['shift']} | {r['tasks_completed']}"
        c.drawString(30, y, line)
        y -= 15

        if y < 50:
            c.showPage()
            y = 750

    c.save()
