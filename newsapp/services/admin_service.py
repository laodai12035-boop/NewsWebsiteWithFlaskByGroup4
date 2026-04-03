from __future__ import annotations

import os
import shutil
from datetime import datetime

from flask import current_app


def backup_database() -> str:
    """Create a timestamped backup of the SQLite database file."""
    base_dir = current_app.config["BASE_DIR"]
    db_path = current_app.config["SQLITE_DB_PATH"]

    backups_dir = os.path.join(base_dir, "backups")
    os.makedirs(backups_dir, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_name = f"news_website_backup_{ts}.db"
    backup_path = os.path.join(backups_dir, backup_name)

    if not os.path.exists(db_path):
        raise FileNotFoundError("Database file not found.")

    shutil.copy2(db_path, backup_path)
    return backup_path

