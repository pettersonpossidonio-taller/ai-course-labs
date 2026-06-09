from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    app = create_app(tmp_path / "shortener.db")
    return TestClient(app)


def test_shorten_url_creates_short_code(client: TestClient) -> None:
    response = client.post("/shorten", json={"url": "https://example.com"})

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"short_code", "short_url"}
    assert len(payload["short_code"]) == 6
    assert payload["short_code"].isalnum()
    assert payload["short_url"].endswith(f"/{payload['short_code']}")


def test_shorten_url_reuses_existing_code(client: TestClient) -> None:
    first = client.post("/shorten", json={"url": "https://example.com"})
    second = client.post("/shorten", json={"url": "https://example.com"})

    assert first.json()["short_code"] == second.json()["short_code"]
    assert first.json()["short_url"] == second.json()["short_url"]


def test_invalid_url_is_rejected(client: TestClient) -> None:
    response = client.post("/shorten", json={"url": "not-a-url"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid URL"


def test_redirects_short_code_to_original_url(client: TestClient) -> None:
    shorten_response = client.post("/shorten", json={"url": "https://example.com"})
    short_code = shorten_response.json()["short_code"]

    response = client.get(f"/{short_code}", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com"
