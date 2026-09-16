from fastapi.testclient import TestClient

from app.main import app


def test_root_endpoint():
    with TestClient(app, raise_server_exceptions=True) as client:
        response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert "message" in data
    assert data["docs_url"] == "/docs"
    assert "api_v1" in data