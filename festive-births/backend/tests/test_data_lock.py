"""Season close: the data becomes read-only at DATA_LOCK_AT (default 10 January 2027, 00:00 SAST)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.config import SAST, Settings, get_settings
from app.models import Role

from .conftest import FACILITY, PASSWORD, login, make_user
from .test_security import DELIVERY

settings = get_settings()


@pytest.fixture
def lock_at(monkeypatch):
    def set_lock(when):
        monkeypatch.setattr(settings, "data_lock_at", when)
    return set_lock


def test_default_lock_is_10_january_2027_sast(monkeypatch):
    monkeypatch.delenv("DATA_LOCK_AT")
    s = Settings(_env_file=None)
    assert s.data_lock_at == datetime(2027, 1, 10, 0, 0, tzinfo=SAST)
    assert not s.data_is_locked(datetime(2027, 1, 9, 21, 59, tzinfo=timezone.utc))  # 23:59 SAST on the 9th
    assert s.data_is_locked(datetime(2027, 1, 9, 22, 0, tzinfo=timezone.utc))       # 00:00 SAST on the 10th


def test_lock_can_be_moved_or_switched_off_by_env(monkeypatch):
    monkeypatch.setenv("DATA_LOCK_AT", "2027-01-15T08:00")
    assert Settings().data_lock_at == datetime(2027, 1, 15, 8, 0, tzinfo=SAST)
    monkeypatch.setenv("DATA_LOCK_AT", "off")
    assert Settings().data_lock_at is None and not Settings().data_is_locked()


def test_before_lock_everything_works(client, lock_at):
    lock_at(datetime.now(timezone.utc) + timedelta(days=1))
    make_user("12345678", Role.user, **FACILITY)
    login(client, "12345678")
    assert client.get("/api/auth/me").json()["data_locked"] is False
    assert client.post("/api/deliveries", json=DELIVERY).status_code == 201


def test_after_lock_data_is_read_only(client, lock_at):
    make_user("12345678", Role.user, **FACILITY)
    login(client, "12345678")
    created = client.post("/api/deliveries", json=DELIVERY).json()

    lock_at(datetime.now(timezone.utc) - timedelta(minutes=1))
    assert client.get("/api/auth/me").json()["data_locked"] is True
    assert client.get("/api/meta").json()["data_locked"] is True

    r = client.post("/api/deliveries", json=DELIVERY)
    assert r.status_code == 423 and "locked" in r.json()["detail"]
    assert client.put(f"/api/deliveries/{created['id']}", json=DELIVERY).status_code == 423
    assert client.delete(f"/api/deliveries/{created['id']}").status_code == 423

    # Reading and exporting still work.
    assert client.get(f"/api/deliveries/{created['id']}").status_code == 200
    assert client.get("/api/deliveries/export").status_code == 200

    # Own password change and sign-out still work.
    r = client.post("/api/auth/change-password", json={"current_password": PASSWORD, "new_password": "BrandNewPass9"})
    assert r.status_code == 200
    assert client.post("/api/auth/logout").status_code == 204
    assert login(client, "12345678", "BrandNewPass9").status_code == 200


def test_after_lock_user_accounts_frozen_but_security_actions_allowed(client, lock_at):
    make_user("12345678", Role.superuser)
    target = make_user("22222222", Role.user, **FACILITY)
    login(client, "12345678")
    lock_at(datetime.now(timezone.utc) - timedelta(minutes=1))

    body = {"first_name": "New", "last_name": "User", "persal_number": "33333333", "role": "user", **FACILITY}
    assert client.post("/api/users", json=body).status_code == 423
    assert client.put(f"/api/users/{target.id}", json={**body, "persal_number": "22222222"}).status_code == 423
    assert client.delete(f"/api/users/{target.id}").status_code == 423

    assert client.post(f"/api/users/{target.id}/reset-password").status_code == 200
    assert client.post(f"/api/users/{target.id}/unlock").status_code == 200
    assert client.post(f"/api/users/{target.id}/revoke-sessions").status_code == 200
    # Path tricks don't open a gap: anything that isn't an exact exempt path stays blocked.
    assert client.post(f"/api/users/{target.id}/reset-password/x").status_code == 423
