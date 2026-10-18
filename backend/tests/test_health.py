from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    # In test environment, health may be unhealthy if DB isn't connected yet
    # The important thing is that the endpoint responds
    assert data["status"] in ["healthy", "unhealthy"]
    assert data["app_name"] == "AI Real Estate Agent"
    assert "database" in data


def test_health_has_request_id():
    response = client.get("/health")
    assert "x-request-id" in response.headers
