import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    # Entering the context runs the app lifespan, which builds settings and providers.
    with TestClient(app) as c:
        yield c


def test_workflow_run(client):
    response = client.post("/api/v1/workflow/run", json={"query": "test query"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_health(client):
    response = client.get("/health/live")
    assert response.status_code == 200
