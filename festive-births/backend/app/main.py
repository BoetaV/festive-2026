import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text

from .config import SAST, get_settings
from .db import SessionLocal
from .models import Role, User
from .routers import auth, dashboard, deliveries, reports, security_center, users
from .security import generate_temp_password, hash_password, password_problems

settings = get_settings()
log = logging.getLogger("festive")


def bootstrap_superuser() -> None:
    """Create the first superuser from env vars (replaces v1's build.sh shell snippet).

    Without SUPERUSER_PASSWORD the account gets a random one-time password, written once to the
    server log, and must change it at first sign-in. (It used to start on a fixed, publicly known
    password, so anyone could claim a freshly deployed instance before its owner did.)
    """
    persal, password = settings.superuser_persal, settings.superuser_password
    if not persal:
        return
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.persal_number == persal)):
            return
        must_change = not password
        if password and (problems := password_problems(password)):
            log.error("SUPERUSER_PASSWORD rejected, needs: %s", ", ".join(problems))
            return
        initial = password or generate_temp_password()
        db.add(User(
            persal_number=persal, first_name="System", last_name="Administrator",
            email=settings.superuser_email, role=Role.superuser,
            hashed_password=hash_password(initial),
            must_change_password=must_change,
        ))
        db.commit()
        if must_change:
            log.warning("Bootstrap superuser %s created with one-time password %s (change it at first sign-in)",
                        persal, initial)
        else:
            log.warning("Bootstrap superuser %s created", persal)


@asynccontextmanager
async def lifespan(_: FastAPI):
    bootstrap_superuser()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Festive Births API",
    version="2.0.0",
    # Interactive docs are handy locally but shouldn't advertise the API surface in production.
    docs_url=None if settings.is_production else "/api/docs",
    openapi_url=None if settings.is_production else "/api/openapi.json",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Protection"],
)

UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}

# Still allowed once the data is locked: signing in and out, changing your own password, and the
# account security actions an administrator may need (reset password, unlock, end sessions).
LOCK_EXEMPT = {"/api/auth/login", "/api/auth/logout", "/api/auth/change-password", "/api/auth/logout-everywhere"}
LOCK_EXEMPT_USER_ACTION = re.compile(r"^/api/users/\d+/(reset-password|unlock|revoke-sessions)$")


def _lock_exempt(path: str) -> bool:
    return path in LOCK_EXEMPT or bool(LOCK_EXEMPT_USER_ACTION.fullmatch(path))


@app.middleware("http")
async def csrf_and_headers(request: Request, call_next):
    # CSRF: browsers can't attach a custom header to a cross-site form post, and
    # cross-origin fetches carrying it need a CORS preflight we only grant to our own origins.
    if request.method in UNSAFE and request.url.path.startswith("/api/") \
            and request.headers.get("x-csrf-protection") != "1":
        return JSONResponse({"detail": "CSRF check failed"}, status_code=403)
    # Season close: after DATA_LOCK_AT the data is read-only (see config.py for what stays allowed).
    if request.method in UNSAFE and settings.data_is_locked() and not _lock_exempt(request.url.path):
        when = settings.data_lock_at.astimezone(SAST).strftime("%d %B %Y")
        return JSONResponse({"detail": f"The festive season database was locked on {when}. "
                                       "Data can still be viewed and exported, but not changed."},
                            status_code=423)
    # Every legitimate payload is a few KB; refuse oversized bodies before they are read into memory.
    length = request.headers.get("content-length")
    if length and (not length.isdigit() or int(length) > settings.max_body_bytes):
        return JSONResponse({"detail": "Request body too large"}, status_code=413)
    if request.method in UNSAFE and not length and request.headers.get("transfer-encoding"):
        return JSONResponse({"detail": "Chunked request bodies are not accepted"}, status_code=411)

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # The API only serves JSON and file downloads: nothing in a response may run or be framed.
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Cache-Control"] = response.headers.get("Cache-Control", "no-store")
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    """Flatten Pydantic errors into {field: message} so forms can show them inline."""
    field_errors: dict[str, str] = {}
    for err in exc.errors():
        loc = [str(p) for p in err["loc"] if p not in ("body", "query", "path")]
        key = ".".join(loc) or "__all__"
        field_errors.setdefault(key, err["msg"].removeprefix("Value error, "))
    return JSONResponse({"detail": {"field_errors": field_errors}}, status_code=422)


for r in (auth, dashboard, deliveries, reports, users, security_center):
    app.include_router(r.router)


@app.get("/api/health", tags=["meta"])
def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok"}
