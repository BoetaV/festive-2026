from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Baby, Delivery, User
from ..schemas import AbnormalWeightRow, NilReportRow
from ..security import any_user, scope_deliveries
from ..services.dashboard import weight_band

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
