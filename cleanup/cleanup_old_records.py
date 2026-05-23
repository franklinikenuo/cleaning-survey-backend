from database import get_db_connection
from cleanup.export_csv import export_to_csv
from cleanup.export_pdf import export_to_pdf
from cleanup.utils import make_archive_paths

def cleanup_old_records():
    conn = get_db_connection()
    conn.row_factory = dict  # or use RealDictCursor depending on your setup
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM submissions
        WHERE timestamp < NOW() - INTERVAL '12 months'
        ORDER BY timestamp ASC
    """)
    records = cur.fetchall()

    if not records:
        return "No old records to archive."

    example_ts = records[0]["timestamp"]
    csv_path, pdf_path = make_archive_paths(example_ts)

    export_to_csv(records, csv_path)
    export_to_pdf(records, pdf_path)

    cur.execute("""
        DELETE FROM submissions
        WHERE timestamp < NOW() - INTERVAL '12 months'
    """)
    conn.commit()

    return f"Archived and deleted {len(records)} records."
