import csv
from cleanup.utils import ensure_dir

def export_to_csv(records, filepath):
    ensure_dir(filepath.rsplit("/", 1)[0])

    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["timestamp", "room", "staff", "shift", "tasks_completed", "notes"])

        for r in records:
            writer.writerow([
                r["timestamp"],
                r["room"],
                r["staff"],
                r["shift"],
                str(r["tasks_completed"]),
                r["notes"] or ""
            ])
