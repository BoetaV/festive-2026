import os
import tempfile

_db = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db}"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-bytes"
os.environ.pop("SUPERUSER_PERSAL", None)
os.environ["DATA_LOCK_AT"] = "off"  # tests must not depend on today's date; test_data_lock sets it explicitly

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Role, User  # noqa: E402
from app.security import hash_password, login_limiter  # noqa: E402

PASSWORD = "Str0ngPassw0rd"
CSRF = {"X-CSRF-Protection": "1"}


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    login_limiter.reset()
    yield


def make_user(persal: str, role: Role, must_change=False, **loc) -> User:
    with SessionLocal() as db:
        u = User(persal_number=persal, first_name="Test", last_name=role.value, role=role,
                 hashed_password=hash_password(PASSWORD), must_change_password=must_change, **loc)
        db.add(u)
        db.commit()
        return u


FACILITY = dict(district="Amathole DM", local_municipality="Mnquma LM", facility="Butterworth Hospital")


@pytest.fixture
def client():
    with TestClient(app) as c:
        c.headers.update(CSRF)
        yield c


def login(client: TestClient, persal: str, password: str = PASSWORD):
    return client.post("/api/auth/login", json={"persal_number": persal, "password": password})
