from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Delivery, User
from ..schemas import DeliveryIn, DeliveryOut, Paged
from ..security import any_user, audit, can_access_delivery, data_editor, scope_deliveries
from ..services.deliveries import FieldErrors, apply_delivery, clean_delivery, to_out
from ..services.exports import XLSX_MIME, deliveries_xlsx

router = APIRouter(prefix="/api/deliveries", tags=["deliveries"])


def _get_scoped(db: Session, user: User, delivery_id: int) -> Delivery:
    d = db.get(Delivery, delivery_id)
    # 404 rather than 403 so out-of-scope record IDs aren't confirmed to exist.
    if not d or not can_access_delivery(user, d):
        raise HTTPException(404, "Delivery not found")
    return d


@router.get("", response_model=Paged[DeliveryOut])
def list_deliveries(
    db: Session = Depends(get_db),
    user: User = Depends(any_user),
    q: str | None = None,
    report_date: date | None = None,
    kind: str | None = Query(None, pattern="^(births|nil)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    stmt = scope_deliveries(select(Delivery), user)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Delivery.facility.ilike(like), Delivery.mother_name.ilike(like),
                              Delivery.mother_surname.ilike(like), Delivery.birth_mode.ilike(like)))
    if report_date:
        stmt = stmt.where(Delivery.report_date == report_date)
    if kind:
        stmt = stmt.where(Delivery.no_births_to_report.is_(kind == "nil"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.options(selectinload(Delivery.babies), selectinload(Delivery.captured_by))
        .order_by(Delivery.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    return Paged(items=[to_out(d) for d in rows], total=total, page=page, page_size=page_size)


@router.get("/export")
def export_deliveries(request: Request, db: Session = Depends(get_db), user: User = Depends(any_user)):
    rows = db.scalars(
        scope_deliveries(select(Delivery), user)
        .options(selectinload(Delivery.babies), selectinload(Delivery.captured_by))
        .order_by(Delivery.created_at)
    )
    content = deliveries_xlsx(rows)
    audit(db, request, "export_deliveries", user=user)
    db.commit()
    return Response(content, media_type=XLSX_MIME,
                    headers={"Content-Disposition": 'attachment; filename="festive_births_full_report.xlsx"'})


@router.get("/{delivery_id}", response_model=DeliveryOut)
def get_delivery(delivery_id: int, db: Session = Depends(get_db), user: User = Depends(any_user)):
    return to_out(_get_scoped(db, user, delivery_id))


@router.post("", response_model=DeliveryOut, status_code=201)
def create_delivery(body: DeliveryIn, request: Request, db: Session = Depends(get_db),
                    user: User = Depends(data_editor)):
    try:
        data = clean_delivery(body, user, db)
    except FieldErrors as e:
        raise HTTPException(422, {"field_errors": e.errors})
    d = Delivery(captured_by_id=user.id)
    apply_delivery(d, data, body)
    db.add(d)
    db.flush()
    audit(db, request, "delivery_created", user=user, detail=f"#{d.id} {d.facility}")
    db.commit()
    db.refresh(d)
    return to_out(d)


@router.put("/{delivery_id}", response_model=DeliveryOut)
def update_delivery(delivery_id: int, body: DeliveryIn, request: Request, db: Session = Depends(get_db),
                    user: User = Depends(data_editor)):
    d = _get_scoped(db, user, delivery_id)
    try:
        data = clean_delivery(body, user, db, existing_id=d.id)
    except FieldErrors as e:
        raise HTTPException(422, {"field_errors": e.errors})
    apply_delivery(d, data, body)
    audit(db, request, "delivery_updated", user=user, detail=f"#{d.id} {d.facility}")
    db.commit()
    db.refresh(d)
    return to_out(d)


@router.delete("/{delivery_id}", status_code=204)
def delete_delivery(delivery_id: int, request: Request, db: Session = Depends(get_db),
                    user: User = Depends(data_editor)):
    d = _get_scoped(db, user, delivery_id)
    audit(db, request, "delivery_deleted", user=user, detail=f"#{d.id} {d.facility} {d.report_date}")
    db.delete(d)
    db.commit()
