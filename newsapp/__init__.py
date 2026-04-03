from __future__ import annotations

import os

from flask import Flask

from .extensions import db


def create_app(test_config: dict | None = None, *, seed: bool = True) -> Flask:
    """Application factory.

    Keeps `app.py` entrypoint small and organizes code by layers:
    - models: `newsapp/models.py`
    - services: `newsapp/services/*`
    - controllers (blueprints): `newsapp/controllers/*`
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    templates_dir = os.path.join(base_dir, "templates")
    static_dir = os.path.join(base_dir, "static")

    app = Flask(__name__, template_folder=templates_dir, static_folder=static_dir)
    app.config["BASE_DIR"] = base_dir

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "your-secret-key-change-in-production")
    db_path = os.path.join(base_dir, "news_website_v2.db")
    app.config["SQLITE_DB_PATH"] = db_path
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path.replace("\\", "/")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Upload limits (2MB default) and allowed extensions.
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", 2 * 1024 * 1024))
    app.config["MAX_IMAGE_BYTES"] = int(os.environ.get("MAX_IMAGE_BYTES", 2 * 1024 * 1024))
    app.config["ALLOWED_IMAGE_EXTENSIONS"] = {"png", "jpg", "jpeg", "webp", "gif"}

    # OpenAI configuration (can be overridden by environment)
    app.config["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY")
    app.config["OPENAI_SUMMARY_MODEL"] = os.environ.get("OPENAI_SUMMARY_MODEL", "gpt-4o-mini")

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    from .controllers.auth_controller import bp as auth_bp
    from .controllers.main_controller import bp as main_bp
    from .controllers.dashboard_controller import bp as dashboard_bp
    from .controllers.editor_controller import bp as editor_bp
    from .controllers.admin_controller import bp as admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(editor_bp)
    app.register_blueprint(admin_bp)

    # Small helper for templates to render image refs consistently.
    @app.template_filter("image_src")
    def image_src_filter(image_ref: str | None) -> str | None:
        if not image_ref:
            return None
        if image_ref.startswith("http://") or image_ref.startswith("https://"):
            return image_ref
        return "/static/" + image_ref.lstrip("/")

    with app.app_context():
        db.create_all()
        _migrate_comment_status(app)
        _migrate_article_ai_fields(app)
        if seed:
            from .seed import seed_if_empty

            seed_if_empty()

    return app


def _migrate_comment_status(app: Flask) -> None:
    """Thêm cột status, review_note vào bảng comments nếu đang dùng SQLite và thiếu cột."""
    import sqlite3

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
    import sqlite3

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

