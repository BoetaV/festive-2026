from datetime import date, datetime, time
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .models import Role

TITLES = ["Mr", "Ms", "Mrs", "Miss", "Dr", "Prof"]
TIME_SLOTS = ["00:01 - 06:00", "06:01 - 12:00", "12:01 - 18:00", "18:01 - 24:00"]
BIRTH_MODES = [
    "Normal Vertex",
    "Caesarean section Elective",
    "Caesarean section Emergency",
    "Vacuum",
    "Forceps",
    "Vaginal Breech",
]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- auth
class LoginIn(BaseModel):
    persal_number: str = Field(min_length=1, max_length=20)
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(max_length=256)


class UserOut(ORM):
    id: int
    persal_number: str
    first_name: str
    last_name: str
    email: str | None
    title: str | None
    designation: str | None
    mobile_number: str | None
    role: Role
    district: str | None
    local_municipality: str | None
    facility: str | None
    is_active: bool
    must_change_password: bool
    last_login_at: datetime | None
    locked_until: datetime | None
    failed_login_attempts: int
    created_at: datetime


# ---------------------------------------------------------------- users
class UserIn(BaseModel):
    first_name: str = Field(min_length=2, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr | None = None
    title: Literal["Mr", "Ms", "Mrs", "Miss", "Dr", "Prof"] | None = None
    designation: str | None = Field(default=None, max_length=100)
    persal_number: str = Field(pattern=r"^\d{8}$", description="8-digit Persal number")
    mobile_number: str | None = Field(default=None, pattern=r"^\d{10}$")
    role: Role
    district: str | None = None
    local_municipality: str | None = None
    facility: str | None = None
    is_active: bool = True

    @field_validator("email", "title", "designation", "mobile_number", "district", "local_municipality", "facility",
                     mode="before")
    @classmethod
    def _blank_to_none(cls, v):
        return v or None


class UserCreated(BaseModel):
    user: UserOut
    temporary_password: str


class PasswordReset(BaseModel):
    temporary_password: str


T = TypeVar("T")


class Paged(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------- deliveries
class BabyIn(BaseModel):
    gender: Literal["Male", "Female"]
    weight: int = Field(ge=200, le=7000, description="grams")


class BabyOut(ORM):
    id: int
    gender: str | None
    weight: int | None


class DeliveryIn(BaseModel):
    district: str | None = None
    local_municipality: str | None = None
    facility: str | None = None
    report_date: date
    time_slot: str | None = None  # only supplied for NIL reports
    no_births_to_report: bool = False
    born_before_arrival: bool = False
    delivery_time: time | None = None
    mother_name: str | None = Field(default=None, max_length=100)
    mother_surname: str | None = Field(default=None, max_length=100)
    mother_dob: date | None = None
    birth_mode: str | None = None
    gravidity: int | None = Field(default=None, ge=0, le=30)
    parity: int | None = Field(default=None, ge=0, le=30)
    babies: list[BabyIn] = Field(default_factory=list, max_length=5)

    @field_validator("district", "local_municipality", "facility", "time_slot", "mother_name",
                     "mother_surname", "birth_mode", mode="before")
    @classmethod
    def _blank_to_none(cls, v):
        return v.strip() or None if isinstance(v, str) else v


class DeliveryOut(ORM):
    id: int
    district: str
    local_municipality: str | None
    facility: str | None
    facility_type: str | None
    report_date: date
    time_slot: str | None
    no_births_to_report: bool
    born_before_arrival: bool
    delivery_time: time | None
    mother_name: str | None
    mother_surname: str | None
    mother_dob: date | None
    mother_age: int | None
    birth_mode: str | None
    gravidity: int | None
    parity: int | None
    babies: list[BabyOut]
    captured_by_name: str | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------- reports
class AbnormalWeightRow(BaseModel):
    baby_id: int
    delivery_id: int
    report_date: date
    facility: str | None
    district: str
    mother_name: str
    gender: str | None
    weight: int
    category: str


class NilReportRow(BaseModel):
    id: int
    report_date: date
    time_slot: str | None
    district: str
    local_municipality: str | None
    facility: str | None
    captured_by_name: str | None
    created_at: datetime


class AuditOut(ORM):
    id: int
    created_at: datetime
    user_id: int | None
    persal_number: str | None
    user_name: str | None = None
    action: str
    success: bool
    ip_address: str | None
    user_agent: str | None
    detail: str | None
