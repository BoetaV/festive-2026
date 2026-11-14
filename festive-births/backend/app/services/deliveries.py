from datetime import date, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..locations import FACILITY_TYPES, is_valid_location
from ..models import Baby, Delivery, Role, User
from ..schemas import BIRTH_MODES, TIME_SLOTS, BabyOut, DeliveryIn, DeliveryOut

MIN_MOTHER_AGE, MAX_MOTHER_AGE = 10, 65


class FieldErrors(Exception):
    def __init__(self, errors: dict[str, str]):
        self.errors = errors


def time_slot_for(t: time) -> str:
    minutes = t.hour * 60 + t.minute
    if minutes == 0:
        return TIME_SLOTS[3]  # midnight belongs to the previous evening's slot
    if minutes <= 6 * 60:
        return TIME_SLOTS[0]
    if minutes <= 12 * 60:
        return TIME_SLOTS[1]
    if minutes <= 18 * 60:
        return TIME_SLOTS[2]
    return TIME_SLOTS[3]


def _age_on(dob: date, on: date) -> int:
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


def clean_delivery(payload: DeliveryIn, user: User, db: Session, existing_id: int | None = None) -> dict:
    """Validates a delivery submission and returns column values. Raises FieldErrors."""
    errors: dict[str, str] = {}
    data = payload.model_dump(exclude={"babies"})

    # --- Location: lock to the user's own scope (v1 made these fields readonly) ---
    if user.role == Role.user:
        data.update(district=user.district, local_municipality=user.local_municipality, facility=user.facility)
    elif user.role == Role.admin:
        data["district"] = user.district

    for f in ("district", "local_municipality", "facility"):
        if not data.get(f):
            errors[f] = "This field is required."
    if not errors and not is_valid_location(data["district"], data["local_municipality"], data["facility"]):
        errors["facility"] = "Facility does not belong to the selected district / sub-district."
    data["facility_type"] = FACILITY_TYPES.get(data.get("facility") or "")

    allowed_dates = get_settings().report_dates
    if payload.report_date not in allowed_dates:
        errors["report_date"] = "Not an active festive-season reporting date."

    if payload.no_births_to_report:
        if payload.time_slot not in TIME_SLOTS:
            errors["time_slot"] = "Select a time slot for a NIL report."
        data["born_before_arrival"] = False
        for f in ("delivery_time", "mother_name", "mother_surname", "mother_dob", "birth_mode", "gravidity", "parity"):
            data[f] = None
        if not errors:
            dup = db.scalar(
                select(Delivery.id).where(
                    Delivery.no_births_to_report.is_(True),
                    Delivery.facility == data["facility"],
                    Delivery.report_date == payload.report_date,
                    Delivery.time_slot == payload.time_slot,
                    Delivery.id != (existing_id or 0),
                )
            )
            if dup:
                errors["time_slot"] = "A NIL report already exists for this facility, date and time slot."
    else:
        for f in ("delivery_time", "mother_name", "mother_surname", "mother_dob", "birth_mode"):
            if not data.get(f):
                errors[f] = "This field is required when reporting a birth."
        if payload.delivery_time:
            data["time_slot"] = time_slot_for(payload.delivery_time)
        if payload.birth_mode and payload.birth_mode not in BIRTH_MODES:
            errors["birth_mode"] = "Unknown birth mode."
        if payload.mother_dob:
            age = _age_on(payload.mother_dob, payload.report_date)
            if not MIN_MOTHER_AGE <= age <= MAX_MOTHER_AGE:
                errors["mother_dob"] = (
                    f"Mother's age must be between {MIN_MOTHER_AGE} and {MAX_MOTHER_AGE}. Calculated age is {age}."
                )
        if payload.gravidity is not None and payload.parity is not None and payload.parity > payload.gravidity:
            errors["parity"] = "Parity cannot exceed gravidity."
        if not payload.babies:
            errors["babies"] = "Add at least one baby."

    if errors:
        raise FieldErrors(errors)
    return data


def apply_delivery(d: Delivery, data: dict, payload: DeliveryIn) -> None:
    for k, v in data.items():
        setattr(d, k, v)
    d.babies.clear()
    if not payload.no_births_to_report:
        d.babies.extend(Baby(gender=b.gender, weight=b.weight) for b in payload.babies)


def to_out(d: Delivery) -> DeliveryOut:
    out = DeliveryOut.model_validate(d)
    out.babies = [BabyOut.model_validate(b) for b in d.babies]
    out.captured_by_name = d.captured_by.full_name if d.captured_by else None
    return out
