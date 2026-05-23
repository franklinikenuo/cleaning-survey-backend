import os
from datetime import datetime

ARCHIVE_ROOT = os.path.join(os.path.dirname(__file__), "..", "archives")

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def make_archive_paths(example_timestamp):
    year = example_timestamp.year
    quarter = (example_timestamp.month - 1) // 3 + 1

    folder = os.path.join(ARCHIVE_ROOT, str(year))
    ensure_dir(folder)

    base = f"submissions_{year}_Q{quarter}"
    csv_path = os.path.join(folder, base + ".csv")
    pdf_path = os.path.join(folder, base + ".pdf")

    return csv_path, pdf_path
