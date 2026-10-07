import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "AI Real Estate Agent"
    assert "database" in data


def test_health_has_request_id():
    response = client.get("/health")
    assert "x-request-id" in response.headers