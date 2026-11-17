from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..config import get_settings
from ..db import get_db
from ..locations import FACILITY_TYPES, LOCATION_DATA, is_valid_location
from ..models import Baby, Delivery, Role, User
from ..schemas import AbnormalWeightRow, NilReportRow
from ..security import any_user, audit, scope_deliveries
from ..services.dashboard import weight_band
from ..services.manual_form import birth_form_pdf, manual_form_pdf

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/abnormal-weights", response_model=list[AbnormalWeightRow])
def abnormal_weights(db: Session = Depends(get_db), user: User = Depends(any_user)):
    stmt = (
        scope_deliveries(select(Baby, Delivery).join(Delivery), user)
        .where((Baby.weight < 2500) | (Baby.weight >= 4000))
        .order_by(Baby.weight)
    )
    return [
        AbnormalWeightRow(
            baby_id=b.id, delivery_id=d.id, report_date=d.report_date, facility=d.facility,
            district=d.district, mother_name=f"{d.mother_name or ''} {d.mother_surname or ''}".strip(),
            gender=b.gender, weight=b.weight, category=weight_band(b.weight),
        )
        for b, d in db.execute(stmt)
    ]


@router.get("/nil", response_model=list[NilReportRow])
def nil_reports(
    db: Session = Depends(get_db),
    user: User = Depends(any_user),
    start_date: date | None = None,
    end_date: date | None = None,
    district: str | None = None,
    local_municipality: str | None = None,
    facility: str | None = None,
):
    stmt = scope_deliveries(select(Delivery), user).where(Delivery.no_births_to_report.is_(True))
    if start_date:
        stmt = stmt.where(Delivery.report_date >= start_date)
    if end_date:
        stmt = stmt.where(Delivery.report_date <= end_date)
    for col, val in ((Delivery.district, district), (Delivery.local_municipality, local_municipality),
                     (Delivery.facility, facility)):
        if val:
            stmt = stmt.where(col == val)
    stmt = stmt.options(selectinload(Delivery.captured_by)).order_by(
        Delivery.report_date.desc(), Delivery.district, Delivery.facility, Delivery.time_slot)
    return [
        NilReportRow(
            id=d.id, report_date=d.report_date, time_slot=d.time_slot, district=d.district,
            local_municipality=d.local_municipality, facility=d.facility,
            captured_by_name=d.captured_by.full_name if d.captured_by else None, created_at=d.created_at,
        )
        for d in db.scalars(stmt)
    ]


def _form_prefill(user: User, report_date: date | None, district: str | None,
                  local_municipality: str | None, facility: str | None) -> dict:
    """Scopes and validates what a printed form is pre-filled with (same rules for every paper form)."""
    if user.role == Role.user:  # facility users always get their own facility
        district, local_municipality, facility = user.district, user.local_municipality, user.facility
    elif user.role == Role.admin:
        if district and district != user.district:
            raise HTTPException(403, "You can only print forms for facilities in your district.")
        district = user.district
    if facility and not local_municipality:  # the facility implies its sub-district
        local_municipality = next((m for m, fs in LOCATION_DATA["facilities"].items() if facility in fs), None)
    if not is_valid_location(district, local_municipality, facility):
        raise HTTPException(422, {"field_errors": {"facility": "Location hierarchy is invalid."}})
    settings = get_settings()
    if report_date and report_date not in settings.report_dates:
        raise HTTPException(422, {"field_errors": {"report_date": "Not a reporting day for this season."}})
    return dict(district=district, local_municipality=local_municipality, facility=facility,
                report_date=report_date, report_dates=settings.report_dates,
                generated_by=f"{user.full_name} ({user.persal_number})")


def _pdf_response(db: Session, request: Request, user: User, pdf: bytes, action: str, name: str,
                  prefill: dict) -> Response:
    where = prefill["facility"] or prefill["district"] or "blank"
    day = prefill["report_date"]
    audit(db, request, action, user=user, detail=f"{where} {day or ''}".strip())
    db.commit()
    slug = "_".join(filter(None, [where.replace(" ", "-"), day.isoformat() if day else None]))
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{name}_{slug}.pdf"'})


@router.get("/manual-form")
def manual_form(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(any_user),
    report_date: date | None = None,
    district: str | None = None,
    local_municipality: str | None = None,
    facility: str | None = None,
    rows: int = Query(30, ge=10, le=100, description="Register rows (one per mother)"),
):
    """End-of-day register: every birth of the day plus NIL time slots, for facilities without connectivity."""
    prefill = _form_prefill(user, report_date, district, local_municipality, facility)
    pdf = manual_form_pdf(**prefill, facility_type=FACILITY_TYPES.get(prefill["facility"] or ""), rows=rows)
    return _pdf_response(db, request, user, pdf, "export_manual_form", "manual_submission_form", prefill)


@router.get("/birth-form")
def birth_form(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(any_user),
    report_date: date | None = None,
    district: str | None = None,
    local_municipality: str | None = None,
    facility: str | None = None,
    copies: int = Query(10, ge=1, le=60, description="Number of forms (two per A4 page)"),
):
    """One-per-birth notification forms, sent to the district immediately after each birth."""
    prefill = _form_prefill(user, report_date, district, local_municipality, facility)
    pdf = birth_form_pdf(**prefill, copies=copies)
    return _pdf_response(db, request, user, pdf, "export_birth_form", "birth_notification_forms", prefill)
