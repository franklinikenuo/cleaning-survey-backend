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

    # Generate PDF in /tmp (Render-safe)
    filepath = "/tmp/dashboard_report.pdf"

    from app.app.dashboard_reportlab import generate_dashboard_pdf
    generate_dashboard_pdf(
        filepath,
        overall_compliance,
        total_submissions,
        top_shift,
        round(avg_tasks, 2)
    )

    return StreamingResponse(
        open(filepath, "rb"),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=cleaning_dashboard.pdf"}
    )
