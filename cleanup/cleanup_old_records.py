from sqlalchemy import text
from main import engine
from cleanup.export_csv import export_to_csv
from cleanup.export_pdf import export_to_pdf
from cleanup.utils import make_archive_paths


def cleanup_old_records():
    """
    Archives and deletes submissions older than 12 months.
    Exports both CSV and PDF versions before deletion.
    """

    # ------------------------------------------------------------
    # 1. Fetch old records
    # ------------------------------------------------------------
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

    # ------------------------------------------------------------
    # 2. Build archive file paths
    # ------------------------------------------------------------
    example_ts = records[0]["timestamp"]
    csv_path, pdf_path = make_archive_paths(example_ts)

    # ------------------------------------------------------------
    # 3. Export to CSV + PDF
    # ------------------------------------------------------------
    export_to_csv(records, csv_path)
    export_to_pdf(records, pdf_path)

    # ------------------------------------------------------------
    # 4. Delete old records
    # ------------------------------------------------------------
    with engine.begin() as conn:
        conn.execute(text("""
            DELETE FROM submissions
            WHERE timestamp < NOW() - INTERVAL '12 months'
        """))

    # ------------------------------------------------------------
    # 5. Return status
    # ------------------------------------------------------------
    return f"Archived and deleted {len(records)} records."
