from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def analyze(self, *, code: str, language: str, analysis_mode: str) -> dict[str, object]:
        self.calls.append(
            {
                "code": code,
                "language": language,
                "analysis_mode": analysis_mode,
            }
        )
        return {
            "summary": f"{analysis_mode} review for {language}.",
            "issues": [
                {
                    "severity": "medium",
                    "line": 2,
                    "category": "maintainability",
                    "description": f"Example {analysis_mode} issue.",
                    "suggestion": "Refactor the example code.",
                }
            ],
            "suggestions": ["Add tests."],
            "metrics": {
                "complexity": "medium",
                "readability": "medium",
                "test_coverage_estimate": "low",
            },
        }


def test_health_endpoint() -> None:
    client = TestClient(create_app(FakeClient()))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_general_mode() -> None:
    fake_client = FakeClient()
    client = TestClient(create_app(fake_client))

    response = client.post(
        "/analyze",
        json={
            "code": "print('hello')\nvalue = 1",
            "language": "python",
            "analysis_mode": "general",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == "general review for python."
    assert body["issues"][0]["severity"] == "medium"
    assert body["metrics"]["test_coverage_estimate"] == "low"
    assert fake_client.calls == [
        {
            "code": "print('hello')\nvalue = 1",
            "language": "python",
            "analysis_mode": "general",
        }
    ]


def test_analyze_security_mode() -> None:
    fake_client = FakeClient()
    client = TestClient(create_app(fake_client))

    response = client.post(
        "/analyze",
        json={
            "code": "password = 'secret'",
            "language": "python",
            "analysis_mode": "security",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == "security review for python."
    assert body["issues"][0]["category"] == "maintainability"
    assert fake_client.calls[-1]["analysis_mode"] == "security"

