from fastapi.testclient import TestClient

from pharmascope.api.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "disclaimer" in body


def test_sources() -> None:
    response = client.get("/api/v1/sources")
    assert response.status_code == 200
    body = response.json()
    keys = {s["key"] for s in body["sources"]}
    assert "openfda_events" in keys
    assert "openfda_ndc" in keys
    assert "openfda_recalls" in keys


def test_prices_not_fabricated() -> None:
    response = client.get("/api/v1/analytics/prices/trends")
    assert response.status_code == 200
    body = response.json()
    assert body["error"] == "dataset_not_configured"
