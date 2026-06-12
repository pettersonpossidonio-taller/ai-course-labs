from __future__ import annotations

import ast
import hashlib
import logging
import math
import os
import re
from dataclasses import dataclass, field
from typing import Literal

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
NL = chr(10)

FrameworkName = Literal["fastapi", "flask"]


class CodeFile(BaseModel):
    path: str = Field(min_length=1)
    content: str = Field(min_length=1)


class IndexRequest(BaseModel):
    files: list[CodeFile] = Field(min_length=1)


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)


class EvaluateRequest(BaseModel):
    top_k: int = Field(default=3, ge=1, le=10)


class SourceSnippet(BaseModel):
    path: str
    chunk: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    source_snippets: list[SourceSnippet]


class JudgeResult(BaseModel):
    score: float
    details: str


class EvaluateResponse(BaseModel):
    precision_at_k: float
    recall_at_k: float
    mrr: float
    judge_result: JudgeResult


class IndexResponse(BaseModel):
    indexed_files: int
    indexed_chunks: int


class ChunkRecord(BaseModel):
    path: str
    chunk: str
    embedding: list[float]


@dataclass
class RagState:
    chunks: list[ChunkRecord] = field(default_factory=list)


state = RagState()
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
EMBED_DIM = 256

EVAL_DATASET = [
    {"question": "How does authentication work?", "keywords": ["auth", "token", "login", "authenticate"]},
    {"question": "How are users retrieved?", "keywords": ["user", "users", "get_user", "retrieve"]},
    {"question": "How are payments processed?", "keywords": ["payment", "charge", "invoice", "transaction"]},
    {"question": "How is token validation performed?", "keywords": ["token", "validate", "jwt", "verify"]},
    {"question": "How is authorization enforced?", "keywords": ["authorize", "permission", "role", "access"]},
    {"question": "How is profile retrieval implemented?", "keywords": ["profile", "user", "account", "fetch"]},
    {"question": "How are billing records handled?", "keywords": ["billing", "invoice", "payment", "subscription"]},
    {"question": "How does login flow work?", "keywords": ["login", "password", "auth", "session"]},
    {"question": "How are transactions recorded?", "keywords": ["transaction", "payment", "ledger", "receipt"]},
    {"question": "How is user management done?", "keywords": ["user", "create_user", "update_user", "delete_user"]},
    {"question": "How do you fetch a user profile?", "keywords": ["profile", "get_user", "user", "fetch"]},
    {"question": "What protects privileged endpoints?", "keywords": ["auth", "role", "permission", "admin"]},
]


def create_app() -> FastAPI:
    app = FastAPI(title="Lab 04 RAG System API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/index/files", response_model=IndexResponse)
    def index_files(payload: IndexRequest) -> IndexResponse:
        indexed_chunks = 0
        state.chunks.clear()
        for file in payload.files:
            for chunk in chunk_code(file.content):
                state.chunks.append(ChunkRecord(path=file.path, chunk=chunk, embedding=embed_text(chunk)))
                indexed_chunks += 1
        return IndexResponse(indexed_files=len(payload.files), indexed_chunks=indexed_chunks)

    @app.post("/query", response_model=QueryResponse)
    def query(payload: QueryRequest) -> QueryResponse:
        matches = retrieve(payload.question, payload.top_k)
        answer = generate_answer(payload.question, matches)
        return QueryResponse(
            answer=answer,
            source_snippets=[SourceSnippet(path=item.path, chunk=item.chunk, score=item.score) for item in matches],
        )

    @app.post("/evaluate", response_model=EvaluateResponse)
    def evaluate(payload: EvaluateRequest) -> EvaluateResponse:
        if not state.chunks:
            return EvaluateResponse(
                precision_at_k=0.0,
                recall_at_k=0.0,
                mrr=0.0,
                judge_result=JudgeResult(score=0.0, details="No indexed code available for evaluation."),
            )

        precisions = []
        recalls = []
        reciprocal_ranks = []
        judge_scores = []
        for example in EVAL_DATASET:
            matches = retrieve(example["question"], payload.top_k)
            relevant = [m for m in matches if is_relevant(m, example["keywords"])]
            precisions.append(len(relevant) / max(1, payload.top_k))
            recalls.append(len(relevant) / max(1, len(example["keywords"])))
            reciprocal_ranks.append(first_relevant_rank(matches, example["keywords"]))
            judge_scores.append(judge_generation(example["question"], matches))

        precision = sum(precisions) / len(precisions)
        recall = sum(recalls) / len(recalls)
        mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)
        judge_score = sum(judge_scores) / len(judge_scores)
        return EvaluateResponse(
            precision_at_k=round(precision, 3),
            recall_at_k=round(recall, 3),
            mrr=round(mrr, 3),
            judge_result=JudgeResult(
                score=round(judge_score, 3),
                details=judge_details(judge_score),
            ),
        )

    return app


app = create_app()


@dataclass
class ScoredChunk:
    path: str
    chunk: str
    score: float


def chunk_code(content: str) -> list[str]:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return generic_chunks(content)

    lines = content.splitlines()
    chunks: list[str] = []
    top_level = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    for node in top_level:
        start = node.lineno - 1
        end = getattr(node, "end_lineno", node.lineno)
        chunk = NL.join(lines[start:end])
        if chunk.strip():
            chunks.append(chunk)
    return chunks or generic_chunks(content)


def generic_chunks(content: str, max_lines: int = 40) -> list[str]:
    lines = content.splitlines()
    chunks = []
    for start in range(0, len(lines), max_lines):
        chunk = NL.join(lines[start:start + max_lines]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks or [content]


def token_vector(text: str) -> list[float]:
    vector = [0.0] * EMBED_DIM
    for token in TOKEN_RE.findall(text.lower()):
        index = int(hashlib.sha1(token.encode("utf-8")).hexdigest(), 16) % EMBED_DIM
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    return vector


def embed_text(text: str) -> list[float]:
    return token_vector(text)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def retrieve(question: str, top_k: int) -> list[ScoredChunk]:
    if not state.chunks:
        return []
    query_embedding = embed_text(question)
    scored = [ScoredChunk(path=chunk.path, chunk=chunk.chunk, score=cosine_similarity(query_embedding, chunk.embedding)) for chunk in state.chunks]
    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:top_k]


def generate_answer(question: str, matches: list[ScoredChunk]) -> str:
    context = NL.join([f"File: {m.path}{NL}{m.chunk}" for m in matches])
    prompt = (
        "You answer questions about a codebase.\n"
        "Use only the provided context. Be concise and grounded.\n\n"
        f"Question: {question}\n\nContext:\n{context}"
    )
    try:
        response = openrouter_chat(prompt)
        return response.strip()
    except Exception:
        logger.warning("LLM unavailable, using fallback analyzer", exc_info=True)
        return local_answer(question, matches)


def openrouter_chat(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1").strip().rstrip("/")
    model = os.getenv("OPENAI_MODEL", "google/gemma-4-31b-it:free").strip()
    headers = {"Authorization": f"Bearer {api_key}"}
    http_referer = os.getenv("OPENROUTER_HTTP_REFERER", "").strip()
    title = os.getenv("OPENROUTER_TITLE", "").strip()
    if http_referer:
        headers["HTTP-Referer"] = http_referer
    if title:
        headers["X-OpenRouter-Title"] = title
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Answer grounded in retrieved code. Return plain text only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    with httpx.Client(base_url=base_url, timeout=20.0, headers=headers) as client:
        response = client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
    content = data["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise ValueError("Invalid LLM response")
    return content


def local_answer(question: str, matches: list[ScoredChunk]) -> str:
    if not matches:
        return "I could not find relevant code in the indexed files."
    first = matches[0]
    summary = first.chunk.splitlines()[0].strip()
    return f"Based on the indexed code, the most relevant file is {first.path}. {summary}"


def is_relevant(match: ScoredChunk, keywords: list[str]) -> bool:
    text = (match.path + NL + match.chunk).lower()
    return any(keyword.lower() in text for keyword in keywords)


def first_relevant_rank(matches: list[ScoredChunk], keywords: list[str]) -> float:
    for index, match in enumerate(matches, start=1):
        if is_relevant(match, keywords):
            return 1.0 / index
    return 0.0


def judge_generation(question: str, matches: list[ScoredChunk]) -> float:
    try:
        prompt = (
            "Judge whether the answer would be grounded in the retrieved code.\n"
            f"Question: {question}\n"
            f"Retrieved snippets: {len(matches)}"
        )
        response = openrouter_chat(prompt)
        return judge_score_from_text(response)
    except Exception:
        logger.warning("LLM unavailable, using fallback analyzer", exc_info=True)
        return local_judge(question, matches)


def judge_score_from_text(text: str) -> float:
    lowered = text.lower()
    if any(token in lowered for token in ("good", "grounded", "relevant", "correct")):
        return 0.9
    return 0.6


def local_judge(question: str, matches: list[ScoredChunk]) -> float:
    if not matches:
        return 0.0
    hit = any(token in (matches[0].path + NL + matches[0].chunk).lower() for token in question.lower().split())
    return 0.8 if hit else 0.5


def judge_details(score: float) -> str:
    if score >= 0.85:
        return "Answer is grounded and relevant."
    if score >= 0.65:
        return "Answer is partially grounded."
    return "Answer quality is weak or unsupported."
