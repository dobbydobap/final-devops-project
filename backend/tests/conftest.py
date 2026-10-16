import os
import pathlib

import pytest

# Point the app at a throwaway SQLite file before anything imports app.config,
# so tests never touch the real Postgres database.
TEST_DB = pathlib.Path(__file__).parent / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"

from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database():
    # A bare TestClient(app) does not run startup events, so the tables have to
    # be created here or the first insert fails with "no such table".
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    TEST_DB.unlink(missing_ok=True)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_assignment(client):
    def _make(**overrides):
        body = {"title": "Sample assignment", "course": "DevOps", "priority": "MEDIUM"}
        body.update(overrides)
        response = client.post("/api/assignments", json=body)
        assert response.status_code == 201, response.text
        return response.json()
    return _make
