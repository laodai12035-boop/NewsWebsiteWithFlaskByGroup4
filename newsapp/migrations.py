"""Lightweight SQLite schema migrations.

These run on every app startup and are idempotent — they only add
columns that are missing.
"""

from __future__ import annotations

import sqlite3

from flask import Flask


def run_migrations(app: Flask) -> None:
    """Run all pending SQLite migrations."""
    _migrate_comment_status(app)
    _migrate_article_ai_fields(app)


def _migrate_comment_status(app: Flask) -> None:
    """Thêm cột status, review_note vào bảng comments nếu đang dùng SQLite và thiếu cột."""
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not uri.startswith("sqlite"):
        return
    path = uri.replace("sqlite:///", "").lstrip("/")
    if path == ":memory:":
        return
    try:
        conn = sqlite3.connect(path)
        cur = conn.execute("PRAGMA table_info(comments)")
        columns = [row[1] for row in cur.fetchall()]
        if "status" not in columns:
            conn.execute("ALTER TABLE comments ADD COLUMN status VARCHAR(20) DEFAULT 'pending'")
        if "review_note" not in columns:
            conn.execute("ALTER TABLE comments ADD COLUMN review_note VARCHAR(500)")
        conn.execute("UPDATE comments SET status = 'approved' WHERE status IS NULL OR status = ''")
        conn.commit()
        conn.close()
    except Exception:
        pass


def _migrate_article_ai_fields(app: Flask) -> None:
    """Add audio_ref, audio_duration, summary_text to articles if missing (SQLite only)."""
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not uri.startswith("sqlite"):
        return
    path = uri.replace("sqlite:///", "").lstrip("/")
    if path == ":memory:":
        return
    try:
        conn = sqlite3.connect(path)
        cur = conn.execute("PRAGMA table_info(articles)")
        columns = [row[1] for row in cur.fetchall()]
        if "audio_ref" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN audio_ref VARCHAR(500)")
        if "audio_duration" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN audio_duration INTEGER")
        if "summary_text" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN summary_text TEXT")
        conn.commit()
        conn.close()
    except Exception:
        pass
