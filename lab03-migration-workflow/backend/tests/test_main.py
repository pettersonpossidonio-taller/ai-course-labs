from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_migrate_returns_required_response_shape() -> None:
    client = TestClient(app)

    response = client.post(
        "/migrate",
        json={
            "source_framework": "fastapi",
            "target_framework": "flask",
            "source_files": [
                {
                    "path": "app.py",
                    "content": "from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/ping')\ndef ping():\n    return {'message': 'pong'}\n",
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["errors"] == []
    assert body["verification_result"]["success"] is True
    assert [step["phase"] for step in body["executed_plan"]] == ["analysis", "planning", "execution", "verification"]
    assert body["executed_plan"][0]["status"] == "completed"
    assert body["executed_plan"][3]["status"] == "completed"
    assert body["migrated_files"][0]["path"] == "app.py"
    assert "Flask" in body["migrated_files"][0]["content"]
