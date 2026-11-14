from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..locations import is_valid_location
from ..models import Role, User
from ..schemas import Paged, PasswordReset, UserCreated, UserIn, UserOut
from ..security import (
    MANAGEABLE_ROLES, audit, can_manage_user, generate_temp_password, hash_password, require_roles, user_manager,
)
from ..services.exports import XLSX_MIME, users_xlsx

router = APIRouter(prefix="/api/users", tags=["users"])


def _scoped(stmt, actor: User):
    if actor.role == Role.superuser:
        return stmt
    if actor.role == Role.province:
        return stmt.where(User.role == Role.admin)
    return stmt.where(User.district == actor.district, User.role == Role.user)


def _get_manageable(db: Session, actor: User, user_id: int) -> User:
    target = db.get(User, user_id)
    if not target or not can_manage_user(actor, target):
        raise HTTPException(404, "User not found")
    return target


def _validate(body: UserIn, actor: User, db: Session, existing: User | None = None) -> None:
    errors: dict[str, str] = {}
    if body.role not in MANAGEABLE_ROLES[actor.role]:
        errors["role"] = ("Province users can only create district users." if actor.role == Role.province
                          else "District users can only create facility users.")
    if actor.role == Role.admin:
        body.district = actor.district
    if existing and existing.id == actor.id and body.role != actor.role:
        errors["role"] = "You cannot change your own role."

    needs = {Role.admin: ("district",), Role.user: ("district", "local_municipality", "facility")}
    for f in needs.get(body.role, ()):
        if not getattr(body, f):
            errors[f] = f"Required for the {body.role.value} role."
    if body.role in (Role.superuser, Role.province):
        body.district = body.local_municipality = body.facility = None
    if body.role == Role.admin:
        body.local_municipality = body.facility = None
    if not errors and not is_valid_location(body.district, body.local_municipality, body.facility):
        errors["facility"] = "Location hierarchy is invalid."

    clash = db.scalar(select(User.id).where(User.persal_number == body.persal_number,
                                            User.id != (existing.id if existing else 0)))
    if clash:
        errors["persal_number"] = "A user with this Persal number already exists."
    if errors:
        raise HTTPException(422, {"field_errors": errors})


@router.get("", response_model=Paged[UserOut])
def list_users(db: Session = Depends(get_db), actor: User = Depends(user_manager), q: str | None = None,
               page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    stmt = _scoped(select(User), actor)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.first_name.ilike(like), User.last_name.ilike(like),
                              User.persal_number.ilike(like), User.district.ilike(like),
                              User.facility.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(User.first_name, User.last_name)
                      .offset((page - 1) * page_size).limit(page_size))
    return Paged(items=list(rows), total=total, page=page, page_size=page_size)


@router.get("/export")
def export_users(request: Request, db: Session = Depends(get_db),
                 actor: User = Depends(require_roles(Role.superuser))):
    content = users_xlsx(db.scalars(select(User).order_by(User.first_name, User.last_name)))
    audit(db, request, "export_users", user=actor)
    db.commit()
    return Response(content, media_type=XLSX_MIME,
                    headers={"Content-Disposition": 'attachment; filename="user_list_report.xlsx"'})


@router.post("", response_model=UserCreated, status_code=201)
def create_user(body: UserIn, request: Request, db: Session = Depends(get_db),
                actor: User = Depends(user_manager)):
    _validate(body, actor, db)
    temp = generate_temp_password()
    user = User(**body.model_dump(), hashed_password=hash_password(temp), must_change_password=True)
    db.add(user)
    db.flush()
    audit(db, request, "user_created", user=actor, detail=f"{user.persal_number} as {user.role.value}")
    db.commit()
    return UserCreated(user=UserOut.model_validate(user), temporary_password=temp)


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserIn, request: Request, db: Session = Depends(get_db),
                actor: User = Depends(user_manager)):
    target = _get_manageable(db, actor, user_id)
    _validate(body, actor, db, existing=target)
    was_active = target.is_active
    for k, v in body.model_dump().items():
        setattr(target, k, v)
    if was_active and not target.is_active:
        target.token_version += 1  # deactivation ends live sessions immediately
    audit(db, request, "user_updated", user=actor, detail=target.persal_number)
    db.commit()
    return target


@router.post("/{user_id}/reset-password", response_model=PasswordReset)
def reset_password(user_id: int, request: Request, db: Session = Depends(get_db),
                   actor: User = Depends(user_manager)):
    target = _get_manageable(db, actor, user_id)
    temp = generate_temp_password()
    target.hashed_password = hash_password(temp)
    target.must_change_password = True
    target.failed_login_attempts = 0
    target.locked_until = None
    target.token_version += 1
    audit(db, request, "password_reset", user=actor, detail=target.persal_number)
    db.commit()
    return PasswordReset(temporary_password=temp)


@router.post("/{user_id}/unlock", response_model=UserOut)
def unlock_user(user_id: int, request: Request, db: Session = Depends(get_db),
                actor: User = Depends(user_manager)):
    target = _get_manageable(db, actor, user_id)
    target.failed_login_attempts = 0
    target.locked_until = None
    audit(db, request, "account_unlocked", user=actor, detail=target.persal_number)
    db.commit()
    return target


@router.post("/{user_id}/revoke-sessions", response_model=UserOut)
def revoke_sessions(user_id: int, request: Request, db: Session = Depends(get_db),
                    actor: User = Depends(user_manager)):
    target = _get_manageable(db, actor, user_id)
    target.token_version += 1
    audit(db, request, "sessions_revoked", user=actor, detail=target.persal_number)
    db.commit()
    return target


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, request: Request, db: Session = Depends(get_db),
                actor: User = Depends(user_manager)):
    target = _get_manageable(db, actor, user_id)
    if target.id == actor.id:
        raise HTTPException(400, "You cannot delete your own account.")
    audit(db, request, "user_deleted", user=actor, detail=f"{target.persal_number} {target.full_name}")
    db.delete(target)
    db.commit()

