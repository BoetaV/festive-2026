from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SAST = timezone(timedelta(hours=2))  # South Africa has no daylight saving


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"  # "development" | "production"
    database_url: str = "postgresql+psycopg://festive:festive@localhost:5445/festive"

    # --- Auth / session ---
    secret_key: str = "dev-insecure-change-me-dev-insecure-change-me"
    session_cookie_name: str = "fb_session"
    session_minutes: int = 30  # sliding idle timeout, same as v1
    session_max_hours: int = 12  # absolute cap: sliding renewal cannot keep a session alive forever
    password_min_length: int = 8
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    login_rate_limit_per_minute: int = 10  # per client IP
    # Wrong current passwords allowed per account on change-password within 15 minutes.
    password_change_attempts: int = 5

    # How many proxies append to X-Forwarded-For in front of the API. 1 = only the Next.js
    # proxy (backend on Railway private networking). Use 2 if the frontend reaches the API
    # through a public Railway domain. The client IP is taken this many entries from the right,
    # because entries further left are supplied by the client and can be forged.
    trusted_proxy_hops: int = 1

    # Largest request body the API accepts (bytes). Every legitimate payload is a few KB.
    max_body_bytes: int = 1_000_000

    # --- Bootstrap superuser (created on startup if missing) ---
    superuser_persal: str | None = None
    superuser_password: str | None = None
    superuser_email: str | None = None

    # --- App ---
    cors_origins: list[str] = ["http://localhost:3010"]
    # Festive-season reporting days users may capture against.
    report_dates: list[date] = [date(2026, 12, 25), date(2027, 1, 1)]

    # From this moment the season's data is read-only: nothing can be captured, edited or deleted
    # and user accounts can't be created, edited or deleted. Viewing, reports and exports keep
    # working, as do sign-in, password changes and account security actions (reset password,
    # unlock, sign out sessions). Override with DATA_LOCK_AT (ISO date-time), or set it to "off".
    data_lock_at: datetime | None = datetime(2027, 1, 10, 0, 0, tzinfo=SAST)

    @field_validator("data_lock_at", mode="before")
    @classmethod
    def _lock_off(cls, v):
        if isinstance(v, str) and v.strip().lower() in ("", "off", "none"):
            return None
        return v

    @field_validator("data_lock_at")
    @classmethod
    def _lock_tz(cls, v: datetime | None) -> datetime | None:
        return v.replace(tzinfo=SAST) if v and v.tzinfo is None else v  # bare times mean SAST

    def data_is_locked(self, now: datetime | None = None) -> bool:
        return self.data_lock_at is not None and (now or datetime.now(timezone.utc)) >= self.data_lock_at

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
