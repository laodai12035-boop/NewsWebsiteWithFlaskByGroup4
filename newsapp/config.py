"""Flask application configuration classes."""

from __future__ import annotations

import os


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload limits (2 MB default) and allowed extensions.
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 2 * 1024 * 1024))
    MAX_IMAGE_BYTES = int(os.environ.get("MAX_IMAGE_BYTES", 2 * 1024 * 1024))
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

    # OpenAI configuration (optional — for AI summary feature).
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    OPENAI_SUMMARY_MODEL = os.environ.get("OPENAI_SUMMARY_MODEL", "gpt-4o-mini")

    # TTS voice (optional override)
    TTS_VOICE = os.environ.get("TTS_VOICE", "vi-VN-HoaiMyNeural")


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
