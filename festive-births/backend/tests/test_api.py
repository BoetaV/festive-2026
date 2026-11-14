from fastapi.testclient import TestClient

from app.main import app
from app.models import Role

from .conftest import FACILITY, PASSWORD, login, make_user

BIRTH = {
    "report_date": "2027-01-01",
    "delivery_time": "03:15",
    "mother_name": "Thandi",
    "mother_surname": "Mokoena",
    "mother_dob": "2010-06-01",  # 16 on the report date -> teen birth
    "birth_mode": "Normal Vertex",
    "gravidity": 1,
    "parity": 1,
    "babies": [{"gender": "Female", "weight": 2300}, {"gender": "Male", "weight": 2600}],
}


# ------------------------------------------------------------------ auth & security
def test_login_success_sets_httponly_cookie(client):
    make_user("12345678", Role.user, **FACILITY)
    r = login(client, "12345678")
    assert r.status_code == 200
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert client.get("/api/auth/me").json()["persal_number"] == "12345678"


def test_wrong_password_and_unknown_user_give_same_message(client):
    make_user("12345678", Role.user, **FACILITY)
    a = login(client, "12345678", "nope")
    b = login(client, "99999999", "nope")
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_account_locks_after_repeated_failures(client):
    make_user("12345678", Role.user, **FACILITY)
    for _ in range(5):
        login(client, "12345678", "wrong")
    r = login(client, "12345678")  # correct password, but locked
    assert r.status_code == 423


def test_ip_rate_limit(client):
    for _ in range(10):
        login(client, "00000000", "x")
    assert login(client, "00000000", "x").status_code == 429


def test_csrf_header_required_for_writes():
    make_user("12345678", Role.user, **FACILITY)
    with TestClient(app) as raw:
        r = raw.post("/api/auth/login", json={"persal_number": "12345678", "password": PASSWORD})
        assert r.status_code == 403 and r.json()["detail"] == "CSRF check failed"


def test_temporary_password_forces_change(client):
    make_user("12345678", Role.user, must_change=True, **FACILITY)
    login(client, "12345678")
    assert client.get("/api/deliveries").status_code == 403
    r = client.post("/api/auth/change-password", json={"current_password": PASSWORD, "new_password": "weak"})
    assert r.status_code == 422 and "new_password" in r.json()["detail"]["field_errors"]
    r = client.post("/api/auth/change-password",
                    json={"current_password": PASSWORD, "new_password": "BrandNewPass9"})
    assert r.status_code == 200
    assert client.get("/api/deliveries").status_code == 200


def test_password_change_revokes_other_sessions(client):
    make_user("12345678", Role.user, **FACILITY)
    with TestClient(app) as other:
        other.headers["X-CSRF-Protection"] = "1"
        login(other, "12345678")
        login(client, "12345678")
        client.post("/api/auth/change-password",
                    json={"current_password": PASSWORD, "new_password": "BrandNewPass9"})
        assert other.get("/api/auth/me").status_code == 401
        assert client.get("/api/auth/me").status_code == 200


def test_security_headers(client):
    r = client.get("/api/health")
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["x-content-type-options"] == "nosniff"


# ------------------------------------------------------------------ deliveries
def test_capture_birth_locks_location_and_derives_fields(client):
    make_user("12345678", Role.user, **FACILITY)
    login(client, "12345678")
    # Tries to post for another district; facility users are pinned to their own facility.
    r = client.post("/api/deliveries", json={**BIRTH, "district": "OR Tambo DM"})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["facility"] == "Butterworth Hospital"
    assert d["facility_type"] == "District Hospital"
    assert d["time_slot"] == "00:01 - 06:00"
    assert d["mother_age"] == 16
    assert len(d["babies"]) == 2


def test_birth_validation_errors(client):
    make_user("12345678", Role.user, **FACILITY)
    login(client, "12345678")
    r = client.post("/api/deliveries", json={**BIRTH, "mother_dob": "2020-01-01", "babies": []})
    errs = r.json()["detail"]["field_errors"]
    assert r.status_code == 422 and "mother_dob" in errs and "babies" in errs


def test_duplicate_nil_report_rejected(client):
    make_user("12345678", Role.user, **FACILITY)
    login(client, "12345678")
    nil = {"report_date": "2027-01-01", "no_births_to_report": True, "time_slot": "06:01 - 12:00"}
    assert client.post("/api/deliveries", json=nil).status_code == 201
    assert client.post("/api/deliveries", json=nil).status_code == 422


def test_province_user_is_read_only_and_scoping(client):
    make_user("11111111", Role.user, **FACILITY)
    make_user("22222222", Role.user, district="OR Tambo DM", local_municipality="Nyandeni LM",
              facility="St Barnabas Hospital")
    make_user("33333333", Role.province)
    login(client, "11111111")
    delivery_id = client.post("/api/deliveries", json=BIRTH).json()["id"]

    login(client, "22222222")  # different facility can't see it
    assert client.get(f"/api/deliveries/{delivery_id}").status_code == 404
    assert client.get("/api/deliveries").json()["total"] == 0

    login(client, "33333333")
    assert client.get("/api/deliveries").json()["total"] == 1
    assert client.post("/api/deliveries", json=BIRTH).status_code == 403


# ------------------------------------------------------------------ dashboard & reports
def test_public_dashboard_kpis(client):
    make_user("12345678", Role.user, **FACILITY)
    login(client, "12345678")
    client.post("/api/deliveries", json=BIRTH)
    client.post("/api/auth/logout")

    k = client.get("/api/dashboard").json()["kpis"]  # no login required
    assert k["total_births"] == 2 and k["males"] == 1 and k["females"] == 1
    assert k["multiple_birth_sets"] == 1
    assert k["teen_births"] == 2
    assert k["low_birth_weight"] == 1 and k["low_birth_weight_rate"] == 50.0

    filtered = client.get("/api/dashboard", params={"district": "OR Tambo DM"}).json()
    assert filtered["kpis"]["total_births"] == 0
    assert filtered["scope"]["level"] == "Sub-district"


def test_exports(client):
    make_user("12345678", Role.superuser)
    login(client, "12345678")
    assert client.get("/api/deliveries/export").content[:2] == b"PK"  # xlsx is a zip
    assert client.get("/api/users/export").content[:2] == b"PK"
    assert client.get("/api/dashboard/pdf").content[:4] == b"%PDF"


# ------------------------------------------------------------------ user management
def test_admin_creates_facility_user_with_default_password_in_own_district(client):
    make_user("12345678", Role.admin, district="Amathole DM")
    login(client, "12345678")
    body = {"first_name": "New", "last_name": "Clerk", "persal_number": "87654321", "role": "user",
            "district": "OR Tambo DM", "local_municipality": "Mnquma LM", "facility": "Butterworth Hospital"}
    r = client.post("/api/users", json=body)
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["user"]["district"] == "Amathole DM"  # forced to admin's district
    assert created["user"]["must_change_password"] is True
    assert created["temporary_password"] == "Password1"

    assert client.post("/api/users", json={**body, "persal_number": "11112222", "role": "admin"}).status_code == 422

    client.post("/api/auth/logout")
    assert login(client, "87654321", "Password1").status_code == 200
    # Must change it before anything else, and may not keep Password1.
    assert client.get("/api/deliveries").status_code == 403
    r = client.post("/api/auth/change-password",
                    json={"current_password": "Password1", "new_password": "Password1"})
    assert r.status_code == 422


def test_province_creates_district_users_only(client):
    make_user("33333333", Role.province)
    make_user("11111111", Role.user, **FACILITY)
    login(client, "33333333")
    district = {"first_name": "Dist", "last_name": "Coord", "persal_number": "44444444", "role": "admin",
                "district": "Amathole DM"}
    r = client.post("/api/users", json=district)
    assert r.status_code == 201, r.text
    assert r.json()["temporary_password"] == "Password1"

    facility = {**district, "persal_number": "55555555", "role": "user", **FACILITY}
    assert client.post("/api/users", json=facility).status_code == 422
    assert client.post("/api/users", json={**district, "persal_number": "66666666",
                                           "role": "superuser"}).status_code == 422
    listed = client.get("/api/users").json()["items"]
    assert {u["persal_number"] for u in listed} == {"44444444"}  # facility users not listed

    new_id = r.json()["user"]["id"]
    assert client.post(f"/api/users/{new_id}/reset-password").json()["temporary_password"] == "Password1"


def test_district_cannot_touch_other_districts_or_district_users(client):
    make_user("12345678", Role.admin, district="Amathole DM")
    make_user("22222222", Role.admin, district="OR Tambo DM")
    make_user("33333333", Role.user, district="OR Tambo DM", local_municipality="Nyandeni LM",
              facility="St Barnabas Hospital")
    login(client, "12345678")
    assert client.get("/api/users").json()["total"] == 0
    for uid in (2, 3):
        assert client.post(f"/api/users/{uid}/reset-password").status_code == 404


def test_security_center(client):
    make_user("12345678", Role.superuser)
    login(client, "00000000", "bad")
    login(client, "12345678")
    o = client.get("/api/security/overview").json()
    assert o["stats"]["failed_logins_24h"] == 1
    assert o["stats"]["logins_24h"] == 1
    actions = {a["action"] for a in client.get("/api/security/audit").json()["items"]}
    assert {"login_failed", "login_success"} <= actions


def test_facility_user_cannot_open_security_center(client):
    make_user("12345678", Role.user, **FACILITY)
    login(client, "12345678")
    assert client.get("/api/security/overview").status_code == 403
    assert client.get("/api/users").status_code == 403


def test_password_minimum_length_is_8(client):
    make_user("12345678", Role.user, **FACILITY)
    login(client, "12345678")
    short = client.post("/api/auth/change-password", json={"current_password": PASSWORD, "new_password": "Abcde12"})
    assert short.status_code == 422 and "8 characters" in short.text
    ok = client.post("/api/auth/change-password", json={"current_password": PASSWORD, "new_password": "Abcdef12"})
    assert ok.status_code == 200, ok.text


def test_only_25_december_and_1_january_are_reporting_days(client):
    make_user("12345678", Role.user, **FACILITY)
    login(client, "12345678")
    assert client.get("/api/meta").json()["report_dates"] == ["2026-12-25", "2027-01-01"]
    assert client.post("/api/deliveries", json={**BIRTH, "report_date": "2026-12-26"}).status_code == 422
    assert client.post("/api/deliveries", json={**BIRTH, "report_date": "2026-12-25"}).status_code == 201
