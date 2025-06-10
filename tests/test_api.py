from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_members_empty():
    """Requires PostgreSQL running."""
    response = client.get("/members")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_digests_empty():
    """Requires PostgreSQL running."""
    response = client.get("/digests")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
