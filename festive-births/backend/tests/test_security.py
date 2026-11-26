"""Regression tests for the November 2026 security hardening (see the November 2026 security review)."""

import io
import time

import jwt
from openpyxl import load_workbook

from app.config import get_settings
from app.db import SessionLocal
from app.models import AuditLog, Delivery, Role
from app.security import JWT_ALG, generate_temp_password, password_change_limiter, password_problems

from .conftest import FACILITY, PASSWORD, login, make_user

settings = get_settings()


def test_temp_passwords_are_random_and_strong():
    pws = {generate_temp_password() for _ in range(50)}
    assert len(pws) == 50
    assert all(not password_problems(p) and len(p) >= 12 for p in pws)


def test_client_ip_ignores_spoofed_left_hand_forwarded_entries(client):
    make_user("12345678", Role.user, **FACILITY)
    client.post("/api/auth/login", json={"persal_number": "12345678", "password": "wrong"},
                headers={"X-Forwarded-For": "6.6.6.6, 10.0.0.9"})
    with SessionLocal() as db:
        assert db.query(AuditLog).order_by(AuditLog.id.desc()).first().ip_address == "10.0.0.9"


def test_login_rate_limit_cannot_be_dodged_by_rotating_forwarded_for(client):
    for i in range(settings.login_rate_limit_per_minute):
        client.post("/api/auth/login", json={"persal_number": "99999999", "password": "x"},
                    headers={"X-Forwarded-For": f"1.2.3.{i}, 10.0.0.9"})
    r = client.post("/api/auth/login", json={"persal_number": "99999999", "password": "x"},
                    headers={"X-Forwarded-For": "8.8.8.8, 10.0.0.9"})
    assert r.status_code == 429


def test_session_has_absolute_lifetime(client):
    u = make_user("12345678", Role.user, **FACILITY)
    old = int(time.time()) - settings.session_max_hours * 3600 - 60
    token = jwt.encode({"sub": str(u.id), "ver": 0, "auth": old, "exp": int(time.time()) + 600},
                       settings.secret_key, algorithm=JWT_ALG)
    client.cookies.set(settings.session_cookie_name, token)
    assert client.get("/api/auth/me").status_code == 401


def test_token_without_auth_time_is_rejected(client):
    u = make_user("12345678", Role.user, **FACILITY)
    token = jwt.encode({"sub": str(u.id), "ver": 0, "exp": int(time.time()) + 600},
                       settings.secret_key, algorithm=JWT_ALG)
    client.cookies.set(settings.session_cookie_name, token)
    assert client.get("/api/auth/me").status_code == 401


def test_change_password_guessing_is_rate_limited(client):
    password_change_limiter.reset()
    make_user("12345678", Role.user, **FACILITY)
    login(client, "12345678")
    for _ in range(settings.password_change_attempts):
        r = client.post("/api/auth/change-password", json={"current_password": "nope", "new_password": "BrandNewPass9"})
        assert r.status_code == 422
    r = client.post("/api/auth/change-password", json={"current_password": PASSWORD, "new_password": "BrandNewPass9"})
    assert r.status_code == 429
    password_change_limiter.reset()


def test_oversized_password_and_body_rejected(client):
    make_user("12345678", Role.user, **FACILITY)
    login(client, "12345678")
    r = client.post("/api/auth/change-password", json={"current_password": "a" * 10_000, "new_password": "x"})
    assert r.status_code == 422
    r = client.post("/api/auth/login", content=b"{" + b" " * (settings.max_body_bytes + 1) + b"}",
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 413


DELIVERY = {"report_date": "2026-12-25", "delivery_time": "10:15", "mother_name": "Thandi",
            "mother_surname": "Mbeki", "mother_dob": "1995-03-02", "birth_mode": "Normal Vertex",
            "babies": [{"gender": "Female", "weight": 3100}]}


def test_formula_and_markup_names_rejected(client):
    make_user("12345678", Role.user, **FACILITY)
    login(client, "12345678")
    for bad in ('=HYPERLINK("http://x","y")', "<b>x</b>", "+27 bad", "@SUM(A1)"):
        r = client.post("/api/deliveries", json={**DELIVERY, "mother_name": bad})
        assert r.status_code == 422 and "mother_name" in r.json()["detail"]["field_errors"], bad
    for ok in ("Nomsa", "O'Brien", "Mary-Jane", "Zoë", "Le Roux"):
        assert client.post("/api/deliveries", json={**DELIVERY, "mother_name": ok}).status_code == 201, ok


def test_excel_export_never_contains_live_formulas(client):
    make_user("12345678", Role.user, **FACILITY)
    login(client, "12345678")
    assert client.post("/api/deliveries", json=DELIVERY).status_code == 201
    with SessionLocal() as db:  # simulate a legacy row that bypassed validation
        d = db.query(Delivery).first()
        d.mother_name = '=HYPERLINK("http://evil","click")'
        db.commit()
    ws = load_workbook(io.BytesIO(client.get("/api/deliveries/export").content)).active
    cells = [c for row in ws.iter_rows(min_row=2) for c in row]
    assert all(c.data_type != "f" for c in cells)
    assert any(isinstance(c.value, str) and "HYPERLINK" in c.value for c in cells)


def test_anonymous_dashboard_hides_facility_level_detail(client):
    r = client.get("/api/dashboard", params={"district": "Amathole DM", "local_municipality": "Mnquma LM",
                                             "facility": "Butterworth Hospital"})
    assert r.status_code == 401
    r = client.get("/api/dashboard")
    assert r.status_code == 200 and r.json()["teen_by_facility"] == [] and r.json()["multiple_births"] == []
    assert client.get("/api/dashboard", params={"district": "Nowhere"}).status_code == 422

    make_user("12345678", Role.user, **FACILITY)
    login(client, "12345678")
    r = client.get("/api/dashboard", params={"district": "Amathole DM", "local_municipality": "Mnquma LM",
                                             "facility": "Butterworth Hospital"})
    assert r.status_code == 200


def test_cannot_deactivate_own_account(client):
    su = make_user("12345678", Role.superuser)
    login(client, "12345678")
    body = {"first_name": "Test", "last_name": "Super", "persal_number": "12345678", "role": "superuser",
            "is_active": False}
    r = client.put(f"/api/users/{su.id}", json=body)
    assert r.status_code == 422 and "is_active" in r.json()["detail"]["field_errors"]


def test_api_responses_carry_security_headers(client):
    r = client.get("/api/health")
    assert r.headers["content-security-policy"].startswith("default-src 'none'")
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["cache-control"] == "no-store"
