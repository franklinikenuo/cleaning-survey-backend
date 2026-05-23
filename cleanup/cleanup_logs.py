import os
from datetime import datetime, timedelta

LOG_DIR = "logs"
RETENTION_DAYS = 30

def cleanup_logs():
    if not os.path.isdir(LOG_DIR):
        return "No logs directory."

    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)

    removed = 0
    for name in os.listdir(LOG_DIR):
        path = os.path.join(LOG_DIR, name)
        if not os.path.isfile(path):
            continue
        mtime = datetime.fromtimestamp(os.path.getmtime(path))
        if mtime < cutoff:
            os.remove(path)
            removed += 1

    return f"Removed {removed} old log files."
