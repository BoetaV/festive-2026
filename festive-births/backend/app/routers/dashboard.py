"""Public dashboard (aggregates only, no patient-identifiable data) and reference data."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..locations import DISTRICTS, FACILITY_TYPES, LOCATION_DATA, is_valid_location
from ..models import Role, User
from ..schemas import BIRTH_MODES, TIME_SLOTS
from ..security import any_user, audit, get_optional_user
from ..services.dashboard import compute_dashboard, filtered_query, last_updated
from ..services.exports import dashboard_pdf
from ..services.reporting import compute_reporting, default_report_date

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/meta")
def meta():
    """Reference data for filters and forms."""
    return {
        "districts": DISTRICTS,
        "municipalities": LOCATION_DATA["municipalities"],
        "facilities": LOCATION_DATA["facilities"],
        "facility_types": FACILITY_TYPES,
        "report_dates": get_settings().report_dates,
        "time_slots": TIME_SLOTS,
        "birth_modes": BIRTH_MODES,
        "data_lock_at": get_settings().data_lock_at,
        "data_locked": get_settings().data_is_locked(),
    }


def _check_filters(district: str | None, local_municipality: str | None, facility: str | None) -> None:
    if not is_valid_location(district, local_municipality, facility):
        raise HTTPException(422, {"field_errors": {"facility": "Location hierarchy is invalid."}})


@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
    report_date: date | None = None,
    district: str | None = None,
    local_municipality: str | None = None,
    facility: str | None = None,
):
    _check_filters(district, local_municipality, facility)
    # Anonymous visitors see district and sub-district aggregates only. One facility on one day
    # is small enough that counts (e.g. mothers aged 10-14, time of birth, birth weight) could
    # identify a patient, so facility-level figures need a signed-in account.
    if facility and viewer is None:
        raise HTTPException(401, "Sign in to view figures for a single facility.")
    stmt = filtered_query(report_date, district, local_municipality, facility)
    data = compute_dashboard(db, stmt, district=district, local_municipality=local_municipality, facility=facility)
    if viewer is None:
        data["teen_by_facility"] = []
        data["multiple_births"] = []
    data["last_updated"] = last_updated(db)
    return data


@router.get("/dashboard/pdf")
def dashboard_report_pdf(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(any_user),
    report_date: date | None = None,
    district: str | None = None,
    local_municipality: str | None = None,
    facility: str | None = None,
):
    _check_filters(district, local_municipality, facility)
    stmt = filtered_query(report_date, district, local_municipality, facility)
    dash = compute_dashboard(db, stmt, district=district, local_municipality=local_municipality, facility=facility)
    title = f"{facility or local_municipality or district or 'Provincial'} Dashboard Report"
    filters = {"Date": report_date, "District": district, "Sub-district": local_municipality, "Facility": facility}
    pdf = dashboard_pdf(dash, title, f"{user.full_name} ({user.persal_number})", filters)
    audit(db, request, "export_dashboard_pdf", user=user, detail=title)
    db.commit()
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="dashboard_report.pdf"'})


@router.get("/dashboard/reporting")
def reporting_compliance(
    db: Session = Depends(get_db),
    user: User = Depends(any_user),
    report_date: date | None = None,
    district: str | None = None,
    local_municipality: str | None = None,
    facility: str | None = None,
):
    """Per facility and time slot: births reported, NIL reported or nothing yet. Signed-in users only;
    district users see their district and facility users their own facility."""
    settings = get_settings()
    if report_date and report_date not in settings.report_dates:
        raise HTTPException(422, {"field_errors": {"report_date": "Not a reporting day for this season."}})
    if user.role == Role.admin:
        if district and district != user.district:
            local_municipality = facility = None
        district = user.district
    elif user.role == Role.user:
        district, local_municipality, facility = user.district, user.local_municipality, user.facility
    return compute_reporting(db, report_date or default_report_date(settings.report_dates),
                             district=district, local_municipality=local_municipality, facility=facility)
