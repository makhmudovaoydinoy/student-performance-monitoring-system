"""Sozlamalar: muhit o'zgaruvchilari (.env yoki Cloud Run env/Secret Manager)."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:  # python-dotenv ixtiyoriy
    pass


class Settings:
    def __init__(self) -> None:
        url = os.getenv("DATABASE_URL", "sqlite:///./student_monitoring.db")
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        self.database_url = url
        self.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")
        self.jwt_algorithm = "HS256"
        self.access_token_minutes = int(os.getenv("ACCESS_TOKEN_MINUTES", "480"))
        self.admin_username = os.getenv("ADMIN_USERNAME", "admin")
        self.admin_password = os.getenv("ADMIN_PASSWORD", "Admin123!")
        self.admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        self.scheduler_token = os.getenv("SCHEDULER_TOKEN", "")
        self.cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.smtp_from = os.getenv("SMTP_FROM", "no-reply@example.com")


settings = Settings()
