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
    app = Flask(__name__, instance_relative_config=True)

    # Chọn config theo môi trường
    flask_env = os.environ.get("FLASK_ENV", "development")
    if flask_env == "production":
        from .config import ProductionConfig
        app.config.from_object(ProductionConfig)
    else:
        from .config import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)

    # Ensure instance folder exists (for database & backups).
    os.makedirs(app.instance_path, exist_ok=True)

    # Database configuration
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        # Render provides postgres://, but SQLAlchemy 1.4+ requires postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    else:
        # Fallback to SQLite path inside instance/.
        db_path = os.path.join(app.instance_path, "news_website_v2.db")
        app.config["SQLITE_DB_PATH"] = db_path
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path.replace("\\", "/")

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
        from .migrations import run_migrations

        run_migrations(app)
        if seed:
            from .seed import seed_if_empty

            seed_if_empty()

    return app
