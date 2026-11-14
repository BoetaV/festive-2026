"""Security Center: authentication health, lockouts and the audit trail."""

from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..config import get_settings
from ..db import get_db
from ..models import AuditLog, Role, User, as_utc
from ..schemas import AuditOut, Paged, UserOut
from ..security import user_manager

router = APIRouter(prefix="/api/security", tags=["security"])

AUTH_FAILURES = ("login_failed", "login_blocked", "login_rate_limited", "account_locked")


def _scope_audit(stmt, actor: User):
    """Superuser and province see everything; district users see their own district only."""
    if actor.role in (Role.superuser, Role.province):
        return stmt
    return stmt.join(User, AuditLog.user_id == User.id).where(User.district == actor.district)


def _scope_users(stmt, actor: User):
    return stmt if actor.role in (Role.superuser, Role.province) else stmt.where(User.district == actor.district)


def _audit_out(a: AuditLog) -> AuditOut:
    out = AuditOut.model_validate(a)
    out.user_name = a.user.full_name if a.user else None
    return out


@router.get("/overview")
def overview(db: Session = Depends(get_db), actor: User = Depends(user_manager)):
    now = datetime.now(timezone.utc)
    day_ago, fortnight = now - timedelta(hours=24), now - timedelta(days=14)
    users = list(db.scalars(_scope_users(select(User), actor)))

    recent = list(db.scalars(
        _scope_audit(select(AuditLog), actor).where(AuditLog.created_at >= fortnight)
        .options(selectinload(AuditLog.user))
    ))
    last_24h = [a for a in recent if as_utc(a.created_at) >= day_ago]

    daily: dict[str, Counter] = {
        (now - timedelta(days=i)).date().isoformat(): Counter() for i in range(13, -1, -1)
    }
    for a in recent:
        key = a.created_at.date().isoformat()
        if key in daily:
            if a.action == "login_success":
                daily[key]["success"] += 1
            elif a.action in AUTH_FAILURES:
                daily[key]["failed"] += 1

    failing = Counter(a.persal_number or "?" for a in last_24h if a.action == "login_failed")
    locked = [u for u in users if u.locked_until and as_utc(u.locked_until) > now]
    s = get_settings()

    return {
        "stats": {
            "total_users": len(users),
            "active_users": sum(u.is_active for u in users),
            "inactive_users": sum(not u.is_active for u in users),
            "locked_accounts": len(locked),
            "pending_password_change": sum(u.must_change_password for u in users),
            "logins_24h": sum(a.action == "login_success" for a in last_24h),
            "failed_logins_24h": sum(a.action == "login_failed" for a in last_24h),
            "rate_limited_24h": sum(a.action == "login_rate_limited" for a in last_24h),
            "never_logged_in": sum(u.last_login_at is None for u in users),
        },
        "users_by_role": [{"role": r.value, "count": sum(u.role == r for u in users)} for r in Role],
        "logins_by_day": [{"date": d, "success": c["success"], "failed": c["failed"]} for d, c in daily.items()],
        "top_failing_persal": [{"persal_number": p, "count": n} for p, n in failing.most_common(5)],
        "locked_users": [UserOut.model_validate(u) for u in locked],
        "pending_users": [UserOut.model_validate(u) for u in users if u.must_change_password][:10],
        "policy": {
            "hashing": "Argon2id",
            "session_idle_minutes": s.session_minutes,
            "max_failed_logins": s.max_failed_logins,
            "lockout_minutes": s.lockout_minutes,
            "login_rate_limit_per_minute": s.login_rate_limit_per_minute,
            "password_min_length": s.password_min_length,
            "secure_cookies": s.is_production,
        },
    }


@router.get("/audit", response_model=Paged[AuditOut])
def audit_log(
    db: Session = Depends(get_db),
    actor: User = Depends(user_manager),
    action: str | None = None,
    success: bool | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    stmt = _scope_audit(select(AuditLog), actor)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if success is not None:
        stmt = stmt.where(AuditLog.success.is_(success))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(AuditLog.persal_number.ilike(like), AuditLog.ip_address.ilike(like),
                              AuditLog.detail.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.options(selectinload(AuditLog.user)).order_by(AuditLog.created_at.desc())
                      .offset((page - 1) * page_size).limit(page_size))
    return Paged(items=[_audit_out(a) for a in rows], total=total, page=page, page_size=page_size)
