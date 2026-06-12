from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


SAMPLE_FILES = [
    {
        "path": "auth.py",
        "content": """
from users import get_user

def authenticate(username, password):
    user = get_user(username)
    if not user:
        return None
    if user.password == password:
        return {"token": "abc123"}
    return None
""".strip(),
    },
    {
        "path": "payments.py",
        "content": """
def process_payment(amount, card):
    if amount <= 0:
        raise ValueError("invalid amount")
    return {"status": "paid", "amount": amount}
""".strip(),
    },
    {
        "path": "users.py",
        "content": """
def get_user(username):
    return {"username": username, "password": "secret"}
""".strip(),
    },
]


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index_query_and_evaluate() -> None:
    client = TestClient(app)

    index_response = client.post("/index/files", json={"files": SAMPLE_FILES})
    assert index_response.status_code == 200
    assert index_response.json()["indexed_files"] == 3

    query_response = client.post("/query", json={"question": "How does authentication work?", "top_k": 3})
    assert query_response.status_code == 200
    query_body = query_response.json()
    assert "answer" in query_body
    assert "source_snippets" in query_body
    assert len(query_body["source_snippets"]) > 0

    eval_response = client.post("/evaluate", json={"top_k": 3})
    assert eval_response.status_code == 200
    eval_body = eval_response.json()
    assert "precision_at_k" in eval_body
    assert "recall_at_k" in eval_body
    assert "mrr" in eval_body
    assert "judge_result" in eval_body


def test_query_falls_back_when_llm_is_unavailable() -> None:
    client = TestClient(app)
    client.post("/index/files", json={"files": SAMPLE_FILES})
    response = client.post("/query", json={"question": "How are payments processed?", "top_k": 2})
    assert response.status_code == 200
    assert response.json()["answer"]
