from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_workflow_run():
    response = client.post("/api/v1/workflow/run", json={"query": "test query"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_health():
    response = client.get("/health/live")
    assert response.status_code == 200
