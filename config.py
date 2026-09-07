import os
from datetime import timedelta


class Config:
    """Base config. Real secrets always come from environment variables —
    never hardcode them here or commit a .env file to git."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")

    # Railway injects DATABASE_URL automatically when you attach a Postgres
    # service. SQLAlchemy needs "postgresql://" not "postgres://" — Railway
    # (and Heroku-style providers) sometimes give the old-style prefix.
    _db_url = os.environ.get("DATABASE_URL", "sqlite:///dev.db")
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Sessions
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Email (e.g. SendGrid/Mailgun SMTP, or Gmail app password for dev)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "info@smile.com")

    # SMS (Termii — built for Nigerian numbers)
    TERMII_API_KEY = os.environ.get("TERMII_API_KEY", "")
    TERMII_SENDER_ID = os.environ.get("TERMII_SENDER_ID", "Smile")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True  # only send cookies over HTTPS


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
