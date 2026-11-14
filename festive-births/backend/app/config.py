from datetime import date
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"  # "development" | "production"
    database_url: str = "postgresql+psycopg://festive:festive@localhost:5445/festive"

    # --- Auth / session ---
    secret_key: str = "dev-insecure-change-me-dev-insecure-change-me"
    session_cookie_name: str = "fb_session"
    session_minutes: int = 30  # sliding idle timeout, same as v1
    password_min_length: int = 8
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    login_rate_limit_per_minute: int = 10  # per client IP

    # Starting password for new / reset accounts; users must change it at first sign-in.
    default_password: str = "Password1"

    # --- Bootstrap superuser (created on startup if missing) ---
    superuser_persal: str | None = None
    superuser_password: str | None = None
    superuser_email: str | None = None

    # --- App ---
    cors_origins: list[str] = ["http://localhost:3010"]
    # Festive-season reporting days users may capture against.
    report_dates: list[date] = [date(2026, 12, 25), date(2027, 1, 1)]

    @field_validator("database_url")
    @classmethod
    def _normalise_db_url(cls, v: str) -> str:
        # Railway/Render hand out postgres:// or postgresql:// URLs; SQLAlchemy needs the driver.
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            v = "postgresql+psycopg://" + v[len("postgresql://"):]
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.is_production and (s.secret_key.startswith("dev-") or len(s.secret_key) < 32):
        raise RuntimeError("SECRET_KEY must be set to a random value of 32+ characters in production")
    return s
