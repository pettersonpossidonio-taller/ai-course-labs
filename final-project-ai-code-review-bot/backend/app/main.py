from __future__ import annotations

import json
import logging
import os
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL_NAME = "google/gemma-3-27b-it:free"

RiskLevel = Literal["Low", "Medium", "High"]
FindingCategory = Literal["Bug", "Security", "Performance", "Style", "Maintainability"]
FindingSeverity = Literal["Critical", "High", "Medium", "Low"]


class AnalyzeRequest(BaseModel):
    code: str = Field(min_length=1)
    language: str = Field(min_length=1)


class Finding(BaseModel):
    category: FindingCategory
    severity: FindingSeverity
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    recommendation: str = Field(min_length=1)


class AnalyzeResponse(BaseModel):
    summary: str = Field(min_length=1)
    risk_level: RiskLevel
    findings: list[Finding]


def create_app() -> FastAPI:
    app = FastAPI(title="AI Code Review Bot API")
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

    @app.post("/analyze", response_model=AnalyzeResponse)
    def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
        try:
            return analyze_code(payload.code, payload.language)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("OpenRouter analysis failed")
            raise HTTPException(status_code=502, detail="LLM request failed") from exc

    return app


app = create_app()


def analyze_code(code: str, language: str) -> AnalyzeResponse:
    client = get_client()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt()},
            {"role": "user", "content": user_prompt(code, language)},
        ],
    )

    content = response.choices[0].message.content
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Empty model response")

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("Model response was not valid JSON") from exc

    try:
        return AnalyzeResponse.model_validate(data)
    except ValidationError as exc:
        raise ValueError("Model response did not match the required schema") from exc


def get_client() -> OpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required")
    return OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)


def system_prompt() -> str:
    return """
You are a senior software engineer performing a professional code review.
Return only valid JSON with this exact structure:
{
  "summary": "Executive summary in 2-4 sentences",
  "risk_level": "Low | Medium | High",
  "findings": [
    {
      "category": "Bug | Security | Performance | Style | Maintainability",
      "severity": "Critical | High | Medium | Low",
      "title": "Short finding title",
      "description": "Clear explanation of the issue",
      "recommendation": "Concrete action to fix it"
    }
  ]
}

Review for:
- Bugs
- Security
- Performance
- Style
- Maintainability

Guidelines:
- Be specific and professional.
- Prefer a concise, actionable review.
- If the code is strong, return a small set of findings.
- Use the requested enum values exactly.
""".strip()


def user_prompt(code: str, language: str) -> str:
    return f"""
Language: {language}

Review the following source code:

```{language}
{code}
```
""".strip()

