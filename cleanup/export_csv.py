import csv
import json
import os
from cleanup.utils import ensure_dir

def export_to_csv(records, filepath):
    """
    Exports a list of record dictionaries to a CSV file.
    Fully compatible with Render and PostgreSQL.
    """

    # Ensure the directory exists
    folder = os.path.dirname(filepath)
    ensure_dir(folder)

    # Write CSV
    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)

        # Header row
        writer.writerow([
            "timestamp",
            "room",
            "staff",
            "shift",
            "tasks_completed",
            "notes"
        ])

        # Data rows
        for r in records:
            writer.writerow([
                r.get("timestamp", ""),
                r.get("room", ""),
                r.get("staff", ""),
                r.get("shift", ""),
                json.dumps(r.get("tasks_completed", {})),  # clean JSON
                r.get("notes", "") or ""
            ])
