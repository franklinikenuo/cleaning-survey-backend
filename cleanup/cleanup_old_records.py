from sqlalchemy import text
from database import engine
from cleanup.export_csv import export_to_csv
from cleanup.export_pdf import export_to_pdf
from cleanup.utils import make_archive_paths


def cleanup_old_records():
    """
    Archives and deletes submissions older than 12 months.
    Exports CSV and PDF before deletion.
    """
    # 1. Fetch old records
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT *
            FROM submissions
            WHERE timestamp < NOW() - INTERVAL '12 months'
            ORDER BY timestamp ASC
        """))
        records = [dict(row) for row in result]

    if not records:
        return "No old records to archive."

    # 2. Build archive paths
    example_ts = records[0]["timestamp"]
    csv_path, pdf_path = make_archive_paths(example_ts)

    # 3. Export
    export_to_csv(records, csv_path)
    export_to_pdf(records, pdf_path)

    # 4. Delete old records
    with engine.begin() as conn:
        conn.execute(text("""
            DELETE FROM submissions
            WHERE timestamp < NOW() - INTERVAL '12 months'
        """))

    return f"Archived and deleted {len(records)} records."
