from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import User, as_utc
from ..schemas import ChangePasswordIn, LoginIn, UserOut
from ..security import (
    any_user, audit, clear_session_cookie, client_ip, get_optional_user, hash_password,
    login_limiter, password_hasher, password_problems, set_session_cookie, verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()

# Verified against when the Persal number is unknown so response time doesn't reveal valid accounts.
_DUMMY_HASH = hash_password("timing-equaliser-not-a-real-password")
INVALID = "Invalid Persal number or password."


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = client_ip(request) or "unknown"
    if not login_limiter.allow(ip):
        audit(db, request, "login_rate_limited", persal_number=body.persal_number, success=False)
        db.commit()
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many login attempts. Wait a minute and try again.")

    persal = body.persal_number.strip()
    user = db.scalar(select(User).where(User.persal_number == persal))
    now = datetime.now(timezone.utc)

    if user is None:
        verify_password(body.password, _DUMMY_HASH)
        audit(db, request, "login_failed", persal_number=persal, success=False, detail="unknown persal number")
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID)

    locked_until = as_utc(user.locked_until)
    if locked_until and locked_until > now:
        audit(db, request, "login_blocked", user=user, success=False, detail="account locked")
        db.commit()
        mins = max(1, int((locked_until - now).total_seconds() // 60) + 1)
        raise HTTPException(status.HTTP_423_LOCKED, f"Account temporarily locked. Try again in {mins} minute(s) or ask an administrator to unlock it.")

    valid, rehashed = password_hasher.verify_and_update(body.password, user.hashed_password)
    if not valid:
        user.failed_login_attempts += 1
        detail = f"attempt {user.failed_login_attempts}/{settings.max_failed_logins}"
        if user.failed_login_attempts >= settings.max_failed_logins:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            user.failed_login_attempts = 0
            audit(db, request, "account_locked", user=user, success=False, detail=f"locked for {settings.lockout_minutes} min")
        audit(db, request, "login_failed", user=user, success=False, detail=detail)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID)

    if not user.is_active:
        audit(db, request, "login_blocked", user=user, success=False, detail="account deactivated")
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated.")

    if rehashed:  # hashing parameters were upgraded since this password was set
        user.hashed_password = rehashed

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    audit(db, request, "login_success", user=user)
    db.commit()
    set_session_cookie(response, user)
    return user


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db),
           user: User | None = Depends(get_optional_user)):
    if user:
        audit(db, request, "logout", user=user)
        db.commit()
    clear_session_cookie(response)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(any_user)):
    return user


@router.post("/change-password", response_model=UserOut)
def change_password(body: ChangePasswordIn, request: Request, response: Response,
                    db: Session = Depends(get_db), user: User = Depends(any_user)):
    if not verify_password(body.current_password, user.hashed_password):
        audit(db, request, "password_change_failed", user=user, success=False, detail="wrong current password")
        db.commit()
        raise HTTPException(422, {"field_errors": {"current_password": "Current password is incorrect."}})
    if body.new_password == body.current_password:
        raise HTTPException(422, {"field_errors": {"new_password": "New password must differ from the current one."}})
    if problems := password_problems(body.new_password, user):
        raise HTTPException(422, {"field_errors": {"new_password": "Password needs " + ", ".join(problems) + "."}})

    user.hashed_password = hash_password(body.new_password)
    user.must_change_password = False
    user.password_changed_at = datetime.now(timezone.utc)
    user.token_version += 1  # signs out every other session
    audit(db, request, "password_changed", user=user)
    db.commit()
    set_session_cookie(response, user)
    return user


@router.post("/logout-everywhere", status_code=204)
def logout_everywhere(request: Request, response: Response, db: Session = Depends(get_db),
                      user: User = Depends(any_user)):
    user.token_version += 1
    audit(db, request, "logout_everywhere", user=user)
    db.commit()
    clear_session_cookie(response)
