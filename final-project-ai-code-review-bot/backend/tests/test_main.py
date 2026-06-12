from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app, analyze_code


class _ChoiceMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _Choice:
    def __init__(self, content: str) -> None:
        self.message = _ChoiceMessage(content)


class _Response:
    def __init__(self, content: str) -> None:
        self.choices = [_Choice(content)]


class _Client:
    class chat:
        class completions:
            @staticmethod
            def create(**_: object) -> _Response:
                return _Response(
                    """
                    {
                      "summary": "The code is readable and mostly straightforward.",
                      "risk_level": "Low",
                      "findings": [
                        {
                          "category": "Style",
                          "severity": "Low",
                          "title": "Minor formatting cleanup",
                          "description": "The code would be easier to scan with consistent formatting.",
                          "recommendation": "Apply the project's formatter and lint rules."
                        }
                      ]
                    }
                    """.strip()
                )


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_schema() -> None:
    original = analyze_code.__globals__["get_client"]
    analyze_code.__globals__["get_client"] = lambda: _Client()
    try:
        result = analyze_code("def add(a, b):\n    return a + b", "python")
        assert result.risk_level == "Low"
        assert result.findings[0].category == "Style"
    finally:
        analyze_code.__globals__["get_client"] = original

