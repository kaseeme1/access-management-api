import pytest

from app.database import connect

API_KEY = "test-key"


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "test.db"))
    yield c
    c.close()


@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setenv("ACCESS_DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("ACCESS_API_KEY", API_KEY)
    with TestClient(app, headers={"X-API-Key": API_KEY}) as c:
        yield c
