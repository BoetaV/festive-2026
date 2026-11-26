"""Authentication, authorisation and audit helpers."""

import re
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from pwdlib import PasswordHash
from sqlalchemy import Select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import AuditLog, Delivery, Role, User

settings = get_settings()
password_hasher = PasswordHash.recommended()  # Argon2id

JWT_ALG = "HS256"
# Paths a user with a temporary password may still reach.
PASSWORD_CHANGE_EXEMPT = {"/api/auth/me", "/api/auth/logout", "/api/auth/change-password"}


# ---------------------------------------------------------------- passwords
def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hasher.verify(password, hashed)


def password_problems(password: str, user: User | None = None) -> list[str]:
    problems = []
    if len(password) < settings.password_min_length:
        problems.append(f"at least {settings.password_min_length} characters")
    if not re.search(r"[a-z]", password):
        problems.append("a lowercase letter")
    if not re.search(r"[A-Z]", password):
        problems.append("an uppercase letter")
    if not re.search(r"\d", password):
        problems.append("a number")
    if user and user.persal_number in password:
        problems.append("must not contain your Persal number")
    if password.lower() in {"password1", "password123", "festive2025", "festive2026", "welcome123"}:
        problems.append("must not be a common password")
    return problems


# No 0/O, 1/l/I: the temporary password is read out over the phone or written down.
_TEMP_LOWER, _TEMP_UPPER, _TEMP_DIGITS = "abcdefghjkmnpqrstuvwxyz", "ABCDEFGHJKMNPQRSTUVWXYZ", "23456789"


def generate_temp_password(length: int = 12) -> str:
    """A random, single-use starting password for new and reset accounts.

    Every account used to start on the same known password, so anyone who knew a new or
    reset user's Persal number could sign in first and take the account over. The account
    is always flagged must_change_password, so this is only ever used once.
    """
    alphabet = _TEMP_LOWER + _TEMP_UPPER + _TEMP_DIGITS
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        if not password_problems(pw):
            return pw


# ---------------------------------------------------------------- sessions
def create_session_token(user: User, auth_time: int | None = None) -> str:
    """auth_time is when the user signed in (epoch seconds); renewals carry it forward so the
    absolute session cap (SESSION_MAX_HOURS) holds however active the session is."""
    now = datetime.now(timezone.utc)
    auth_time = auth_time or int(now.timestamp())
    hard_stop = datetime.fromtimestamp(auth_time, timezone.utc) + timedelta(hours=settings.session_max_hours)
    payload = {
        "sub": str(user.id),
        "ver": user.token_version,
        "iat": now,
        "auth": auth_time,
        "exp": min(now + timedelta(minutes=settings.session_minutes), hard_stop),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALG)


def set_session_cookie(response: Response, user: User, auth_time: int | None = None) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        create_session_token(user, auth_time),
        max_age=settings.session_minutes * 60,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(settings.session_cookie_name, path="/", httponly=True,
                           secure=settings.is_production, samesite="lax")


def client_ip(request: Request) -> str | None:
    """The address TRUSTED_PROXY_HOPS entries from the right of X-Forwarded-For.

    Left-hand entries are whatever the client sent, so trusting the first one let anyone
    dodge the per-IP login limit and write a fake address into the audit log.
    """
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        chain = [p.strip() for p in fwd.split(",") if p.strip()]
        if chain:
            return chain[-min(settings.trusted_proxy_hops, len(chain))][:64]
    return request.client.host if request.client else None


def _session_from_cookie(request: Request, db: Session) -> tuple[User, int] | None:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALG],
                             options={"require": ["exp", "sub", "ver", "auth"]})
        user_id, auth_time = int(payload["sub"]), int(payload["auth"])
    except (jwt.PyJWTError, ValueError, TypeError):
        return None
    if time.time() - auth_time > settings.session_max_hours * 3600:
        return None
    user = db.get(User, user_id)
    if not user or not user.is_active or payload.get("ver") != user.token_version:
        return None
    return user, auth_time


def _user_from_cookie(request: Request, db: Session) -> User | None:
    session = _session_from_cookie(request, db)
    return session[0] if session else None


def get_current_user(request: Request, response: Response, db: Session = Depends(get_db)) -> User:
    session = _session_from_cookie(request, db)
    if not session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    user, auth_time = session
    if user.must_change_password and request.url.path not in PASSWORD_CHANGE_EXEMPT:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "password_change_required")
    # Sliding expiry: every authenticated request renews the idle timer (v1: SESSION_SAVE_EVERY_REQUEST),
    # but never past SESSION_MAX_HOURS after sign-in.
    request.state.auth_time = auth_time
    set_session_cookie(response, user, auth_time)
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    return _user_from_cookie(request, db)


def require_roles(*roles: Role):
    def dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission for this action")
        return user

    return dep


# Shorthand dependencies
any_user = get_current_user
data_editor = require_roles(Role.superuser, Role.admin, Role.user)  # province does not capture data
user_manager = require_roles(Role.superuser, Role.province, Role.admin)

# Which roles each manager may create / manage.
#   superuser -> anyone; province -> district and facility users; district (admin) -> facility users in own district
MANAGEABLE_ROLES = {
    Role.superuser: {Role.superuser, Role.province, Role.admin, Role.user},
    Role.province: {Role.admin, Role.user},
    Role.admin: {Role.user},
}


# ---------------------------------------------------------------- data scoping
def scope_deliveries(stmt: Select, user: User) -> Select:
    """Restricts a Delivery query to what the user is allowed to see."""
    if user.role in (Role.superuser, Role.province):
        return stmt
    if user.role == Role.admin:
        return stmt.where(Delivery.district == user.district)
    return stmt.where(Delivery.facility == user.facility)


def can_access_delivery(user: User, d: Delivery) -> bool:
    if user.role in (Role.superuser, Role.province):
        return True
    if user.role == Role.admin:
        return d.district == user.district
    return d.facility == user.facility


def can_manage_user(actor: User, target: User) -> bool:
    if actor.role == Role.superuser:
        return True
    if actor.role == Role.province:
        return target.role in (Role.admin, Role.user)
    return (
        actor.role == Role.admin
        and target.role == Role.user
        and target.district == actor.district
    )


# ---------------------------------------------------------------- rate limiting
class SlidingWindowLimiter:
    """In-process limiter; adequate for a single Railway replica.

    Per-account lockout (stored in the DB) is the primary brute-force defence and
    works across replicas; this only blunts credential-spraying from one IP.
    """

    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit, self.window = limit, window_seconds
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self.lock:
            if len(self.hits) > 10_000:  # keep memory bounded: drop keys with no recent hits
                for k in [k for k, v in self.hits.items() if not v or v[-1] <= now - self.window]:
                    del self.hits[k]
            q = self.hits[key]
            while q and q[0] <= now - self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True

    def forget(self, key: str) -> None:
        with self.lock:
            self.hits.pop(key, None)

    def reset(self) -> None:
        with self.lock:
            self.hits.clear()


login_limiter = SlidingWindowLimiter(settings.login_rate_limit_per_minute)
# Stops someone holding a stolen session from guessing the current password to take the account over.
password_change_limiter = SlidingWindowLimiter(settings.password_change_attempts, window_seconds=15 * 60)


# ---------------------------------------------------------------- audit
def audit(
    db: Session,
    request: Request | None,
    action: str,
    *,
    user: User | None = None,
    persal_number: str | None = None,
    success: bool = True,
    detail: str | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            persal_number=persal_number or (user.persal_number if user else None),
            action=action,
            success=success,
            ip_address=client_ip(request) if request else None,
            user_agent=(request.headers.get("user-agent") or "")[:255] if request else None,
            detail=detail,
        )
    )
