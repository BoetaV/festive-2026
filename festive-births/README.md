# Festive Births 2026

ECDoH festive-season births dashboard and capture system (2026/27 season: 25 Dec 2026 and 1 Jan 2027).
The old 2025 Django app is kept in `../_archive_2025_django/` for reference.

| Layer | Stack |
|---|---|
| API | FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL (psycopg 3) |
| Web | Next.js 16 (App Router) · Tailwind CSS 4 · shadcn/ui (Base UI) · Recharts |
| Ops | Docker · docker-compose (local) · Railway (production) |

```
festive-births/
├── backend/            FastAPI app (app/), Alembic migrations, tests
├── frontend/           Next.js app (src/app), /api proxy route, proxy.ts route guard
└── docker-compose.yml  Postgres for dev; `--profile full` runs the whole stack
```

## Run with Docker (recommended)

```bash
docker compose up -d --build     # Postgres + API + web
```

Open **http://localhost:3010** and sign in with Persal **00000001** and the one-time password printed in the backend log (`docker compose logs backend | grep "one-time password"`). You will be asked to set a new password.

Ports: **web 3010 · API 8010 · Postgres 5445**. `docker compose down` stops everything; data is kept in the `pgdata` volume.

## Users and roles

Everyone signs in with their **8-digit Persal number**. New and reset accounts get a **random one-time password**, shown once to the administrator who created or reset the account, and must change it to a strong password at first sign-in. Hand it over in person or by phone.

| Role | Created by | Sees | Can create |
|---|---|---|---|
| Superuser | (bootstrap) | Whole province | Any role |
| Province | Superuser | Whole province (does not capture) | District users |
| District | Superuser, Province | Own district | Facility users in own district |
| Facility | Superuser, District | **Own facility only**: births, NIL reports, reports, exports | – |

## Run natively (hot reload)

```bash
docker compose up -d db
cd backend && .venv/Scripts/alembic upgrade head && .venv/Scripts/uvicorn app.main:app --reload --port 8010
cd frontend && npm run dev
```

Optional demo data: `cd backend && .venv/Scripts/python -m app.seed --reset` (demo password `Festive2026!`, development only).
Tests: `cd backend && .venv/Scripts/python -m pytest`

## What's in the app

- **`/`: public dashboard.** Live KPI tiles (births, sex split, deliveries, NIL reports, facilities reporting, low birth weight, teen births, caesarean rate, BBA, multiple births, average weight), drill-down filters (date → district → sub-district → facility), charts with a table view, plus the **Access & security** section showing roles, controls and the role-gated work areas.
- **`/app`: workspace.** Capture births / NIL reports, delivery records, reports (abnormal weights, NIL), Excel/PDF exports, user management, Security Center.
- **Security Center**: sign-in activity, failed logins, locked accounts (one-click unlock), pending temp passwords, policy summary, and a searchable audit trail.

### Security model

- Argon2id password hashing; strong-password policy (8+ chars, mixed case, digit).
- New and reset accounts get a random one-time password. Users must change it before anything else works.
- Sessions: 30-minute sliding idle timeout, 12-hour absolute maximum (`SESSION_MAX_HOURS`).
- **Season lock:** from **10 January 2027, 00:00 SAST** (`DATA_LOCK_AT`) the database is read-only. Births, NIL reports and user accounts can no longer be added, changed or deleted (the API answers 423 and the UI hides editing). Dashboards, reports and exports keep working, as do sign-in, own password changes and administrator reset password / unlock / sign out sessions. To reopen for corrections, set `DATA_LOCK_AT` to a later time or `off` on the backend service and redeploy.
- Lockout after 5 failed sign-ins (15 min), plus a per-IP rate limit; identical errors for unknown vs wrong password.
- Session = signed JWT in an **httpOnly, SameSite=Lax** cookie (Secure in production), 30-minute sliding idle timeout. A password change, deactivation or "sign out everywhere" revokes every session.
- CSRF: every write must carry `X-CSRF-Protection: 1`, which cross-site forms cannot send.
- Least-privilege scoping on the server: facility users see only their facility; district users see their district; province users see the province but do not capture data.
- Audit log of sign-ins, changes, exports and admin actions. Security headers on both apps. API docs are disabled in production.

## Deploy to Railway

Create one Railway project with **three services** from this repo:

1. **PostgreSQL**: add the Railway Postgres plugin.
2. **backend**: root directory `backend` (uses `backend/Dockerfile` + `railway.json`; runs `alembic upgrade head` on start). Variables:
   - `ENVIRONMENT=production`
   - `HOST=::` and `PORT=8000`: listen on IPv6 too, which Railway's private network uses
   - `DATABASE_URL=${{Postgres.DATABASE_URL}}`
   - `SECRET_KEY=` a random value: `python -c "import secrets; print(secrets.token_urlsafe(48))"`
   - `SUPERUSER_PERSAL`: your first admin account (created on first boot; set `SUPERUSER_PASSWORD` too, or read the random one-time password from the deploy log; must be changed at first sign-in)
   - `REPORT_DATES=["2026-12-25","2027-01-01"]`: set this season's reporting days
   - **Do not give this service a public domain.** Only the frontend should reach it, over Railway's private network.
3. **frontend**: root directory `frontend`. Variables:
   - `BACKEND_URL=http://${{backend.RAILWAY_PRIVATE_DOMAIN}}:${{backend.PORT}}`
   - Generate a public domain for this service.

The browser only ever talks to the frontend; `/api/*` is proxied server-side, so cookies stay first-party and no CORS setup is needed.

## Open items

- `app/locations.py` still lacks a facility type for: Bedford Hospital, Graaff-Reinet Day Hospital, Mjanyana Hospital, Port Elizabeth Provincial Hospital, St Francis Hospital (they show as "Unknown").
- Migrating v1 data: export the old Postgres tables and map `report_date` text (e.g. "01 January 2026") to real dates. Old users should be re-created with temporary passwords, because Django password hashes are not carried over.
- The per-IP login limiter is in-memory, which is fine for one backend replica. Use Redis if you scale out.
