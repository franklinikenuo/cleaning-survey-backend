import os
from datetime import datetime, timedelta

LOG_DIR = "logs"
RETENTION_DAYS = 30


def cleanup_logs():
    """
    Deletes log files older than RETENTION_DAYS.
    Safe for production and Render deployments.
    """
    if not os.path.isdir(LOG_DIR):
        return "Logs directory does not exist. No cleanup needed."

    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    removed = 0

    for filename in os.listdir(LOG_DIR):
        path = os.path.join(LOG_DIR, filename)

        if not os.path.isfile(path):
            continue

        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
        except Exception:
            continue

        if mtime < cutoff:
            try:
                os.remove(path)
                removed += 1
            except Exception:
                continue

    return f"Removed {removed} old log files."
