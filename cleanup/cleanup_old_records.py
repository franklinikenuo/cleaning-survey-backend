import os
from datetime import datetime, timedelta
from sqlalchemy import text
from database import SessionLocal, Submission
from dashboard_reportlab import generate_dashboard_pdf
from cleanup.export_csv import export_to_csv
from cleanup.utils import make_archive_paths


def cleanup_old_records():
    """
    Archives and deletes submissions older than 12 months.
    Exports CSV and PDF before deletion.
    Fully compatible with PostgreSQL + Render.
    """

    db = SessionLocal()

    try:
        # 1. Fetch old records
        cutoff = datetime.utcnow() - timedelta(days=365)

        records = (
            db.query(Submission)
            .filter(Submission.timestamp < cutoff)
            .order_by(Submission.timestamp.asc())
            .all()
        )

        if not records:
            return "No old records to archive."

        # Convert ORM objects to dicts
        dict_records = []
        for r in records:
            dict_records.append({
                "id": r.id,
                "room": r.room,
                "shift": r.shift,
                "staff": r.staff,
                "tasks_completed": r.tasks_completed,
                "notes": r.notes,
                "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            })

        # 2. Build archive paths
        example_ts = records[0].timestamp
        csv_path, pdf_path = make_archive_paths(example_ts)

        os.makedirs(os.path.dirname(csv_path), exist_ok=True)

        # 3. Export CSV
        export_to_csv(dict_records, csv_path)

        # 4. Compute KPIs for PDF
        total_submissions = len(records)

        avg_tasks = (
            sum(len(r.tasks_completed) for r in records) / total_submissions
            if total_submissions > 0 else 0
        )

        shift_counts = {}
        for r in records:
            shift_counts[r.shift] = shift_counts.get(r.shift, 0) + 1

        top_shift = max(shift_counts, key=shift_counts.get)

        # 5. Export PDF
        generate_dashboard_pdf(
            pdf_path,
            overall_compliance=92,
            total_submissions=total_submissions,
            top_shift=top_shift,
            avg_tasks=round(avg_tasks, 2)
        )

        # 6. Delete old records
        for r in records:
            db.delete(r)

        db.commit()

        return f"Archived and deleted {len(records)} records."

    finally:
        db.close()
