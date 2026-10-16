import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    assert client.get("/health").json() == {"status": "UP"}

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "StudyDesk API"

def test_create_assignment():
    response = client.post("/api/assignments", json={"title": "Helm lab", "course": "DevOps", "priority": "HIGH"})
    assert response.status_code == 201
    assert response.json()["title"] == "Helm lab"
    assert response.json()["status"] == "PENDING"

def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
