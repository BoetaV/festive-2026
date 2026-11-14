import enum
from datetime import date, datetime, time, timezone

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime | None) -> datetime | None:
    """SQLite hands back naive datetimes; treat them as UTC so comparisons work on both DBs."""
    return dt.replace(tzinfo=timezone.utc) if dt and dt.tzinfo is None else dt


class Role(str, enum.Enum):
    """Replaces v1's Django groups.

    superuser - everything, including all user management
    province  - views the whole province, creates/manages district users (does not capture data)
    admin     - "District" user: sees one district, creates/manages that district's facility users
    user      - "Facility" user: captures and sees data for one facility only
    """

    superuser = "superuser"
    province = "province"
    admin = "admin"
    user = "user"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    persal_number: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(10))
    designation: Mapped[str | None] = mapped_column(String(100))
    mobile_number: Mapped[str | None] = mapped_column(String(10))

    role: Mapped[Role] = mapped_column(Enum(Role, name="user_role"), default=Role.user)
    district: Mapped[str | None] = mapped_column(String(100))
    local_municipality: Mapped[str | None] = mapped_column(String(100))
    facility: Mapped[str | None] = mapped_column(String(100))

    # --- Security ---
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Bumped on password change / forced sign-out; invalidates every issued session token.
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    district: Mapped[str] = mapped_column(String(100), index=True)
    local_municipality: Mapped[str | None] = mapped_column(String(100), index=True)
    facility: Mapped[str | None] = mapped_column(String(100), index=True)
    facility_type: Mapped[str | None] = mapped_column(String(100))

    report_date: Mapped[date] = mapped_column(Date, index=True)
    time_slot: Mapped[str | None] = mapped_column(String(20))

    no_births_to_report: Mapped[bool] = mapped_column(Boolean, default=False)
    born_before_arrival: Mapped[bool] = mapped_column(Boolean, default=False)
    delivery_time: Mapped[time | None] = mapped_column(Time)
    mother_name: Mapped[str | None] = mapped_column(String(100))
    mother_surname: Mapped[str | None] = mapped_column(String(100))
    mother_dob: Mapped[date | None] = mapped_column(Date)
    birth_mode: Mapped[str | None] = mapped_column(String(100))
    gravidity: Mapped[int | None] = mapped_column(Integer)
    parity: Mapped[int | None] = mapped_column(Integer)

    captured_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    captured_by: Mapped[User | None] = relationship()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    babies: Mapped[list["Baby"]] = relationship(
        back_populates="delivery", cascade="all, delete-orphan", order_by="Baby.id"
    )

    @property
    def mother_age(self) -> int | None:
        """Mother's age on the day of delivery (v1 used 'today', which drifts every year)."""
        if not self.mother_dob:
            return None
        d, b = self.report_date, self.mother_dob
        return d.year - b.year - ((d.month, d.day) < (b.month, b.day))


class Baby(Base):
    __tablename__ = "babies"

    id: Mapped[int] = mapped_column(primary_key=True)
    delivery_id: Mapped[int] = mapped_column(ForeignKey("deliveries.id", ondelete="CASCADE"), index=True)
    gender: Mapped[str | None] = mapped_column(String(10))
    weight: Mapped[int | None] = mapped_column(Integer)  # grams

    delivery: Mapped[Delivery] = relationship(back_populates="babies")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    persal_number: Mapped[str | None] = mapped_column(String(20))  # as typed, for failed logins
    action: Mapped[str] = mapped_column(String(50), index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    detail: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User | None] = relationship()
