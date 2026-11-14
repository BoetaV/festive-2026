import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text

from .config import get_settings
from .db import SessionLocal
from .models import Role, User
from .routers import auth, dashboard, deliveries, reports, security_center, users
from .security import hash_password, password_problems

settings = get_settings()
log = logging.getLogger("festive")


def bootstrap_superuser() -> None:
    """Create the first superuser from env vars (replaces v1's build.sh shell snippet)."""
    """Without SUPERUSER_PASSWORD the account starts on DEFAULT_PASSWORD and must change it at first sign-in."""
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
        db.add(User(
            persal_number=persal, first_name="System", last_name="Administrator",
            email=settings.superuser_email, role=Role.superuser,
            hashed_password=hash_password(password or settings.default_password),
            must_change_password=must_change,
        ))
        db.commit()
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


@app.middleware("http")
async def csrf_and_headers(request: Request, call_next):
    # CSRF: browsers can't attach a custom header to a cross-site form post, and
    # cross-origin fetches carrying it need a CORS preflight we only grant to our own origins.
    if request.method in UNSAFE and request.url.path.startswith("/api/") \
            and request.headers.get("x-csrf-protection") != "1":
        return JSONResponse({"detail": "CSRF check failed"}, status_code=403)

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
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
