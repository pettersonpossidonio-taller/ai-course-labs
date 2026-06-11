from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from .schemas import AnalysisMode


class AnalysisClient(Protocol):
    def analyze(self, *, code: str, language: str, analysis_mode: AnalysisMode) -> dict[str, Any]:
        ...


def build_system_prompt(analysis_mode: AnalysisMode) -> str:
    base = """
You are a code analysis assistant.
Return only valid JSON matching this schema:
{
  "summary": "2-3 sentence overview",
  "issues": [
    {
      "severity": "high|medium|low",
      "line": 1,
      "category": "bug|security|performance|style|maintainability",
      "description": "...",
      "suggestion": "..."
    }
  ],
  "suggestions": ["..."],
  "metrics": {
    "complexity": "...",
    "readability": "...",
    "test_coverage_estimate": "..."
  }
}

Rules:
- Use concise plain language.
- Always include all top-level keys.
- If there are no issues, return an empty issues array.
- Use 1-based line numbers when possible.
""".strip()

    if analysis_mode == "security":
        focus = """
Security focus:
- Prioritize injection risks, authentication/authorization issues, unsafe parsing, secrets exposure, and missing input validation.
- Categorize security findings as "security" when appropriate.
""".strip()
    else:
        focus = """
General focus:
- Look for correctness bugs, performance problems, style issues, and maintainability concerns.
- Prefer a balanced review with practical suggestions.
""".strip()

    return f"{base}\n\n{focus}"


def parse_json_object(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match is None:
            raise
        value = json.loads(match.group(0))

    if not isinstance(value, dict):
        raise ValueError("LLM response was not a JSON object")
    return value


@dataclass
class OpenAICompatibleClient:
    api_key: str
    model: str
    base_url: str = "https://api.openai.com/v1"
    http_referer: str | None = None
    app_title: str | None = None
    timeout: float = 30.0

    def analyze(self, *, code: str, language: str, analysis_mode: AnalysisMode) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": build_system_prompt(analysis_mode)},
                {
                    "role": "user",
                    "content": (
                        f"Language: {language}\n"
                        f"Analysis mode: {analysis_mode}\n\n"
                        f"Code:\n{code}"
                    ),
                },
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        headers = {"Authorization": f"Bearer {self.api_key}"}
        if self.http_referer:
            headers["HTTP-Referer"] = self.http_referer
        if self.app_title:
            headers["X-OpenRouter-Title"] = self.app_title
        with httpx.Client(base_url=self.base_url.rstrip("/"), timeout=self.timeout, headers=headers) as client:
            response = client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("Unexpected OpenAI-compatible response shape") from exc

        if not isinstance(content, str):
            raise ValueError("Unexpected OpenAI-compatible message content")

        return parse_json_object(content)


class RuleBasedAnalysisClient:
    def analyze(self, *, code: str, language: str, analysis_mode: AnalysisMode) -> dict[str, Any]:
        lines = code.splitlines()
        issues: list[dict[str, Any]] = []
        suggestions: list[str] = []

        for line_number, line in enumerate(lines, start=1):
            stripped = line.strip()
            if "eval(" in stripped:
                issues.append(
                    {
                        "severity": "high",
                        "line": line_number,
                        "category": "security",
                        "description": "Use of eval can execute arbitrary code.",
                        "suggestion": "Replace eval with a safe parser or explicit branching.",
                    }
                )
            if any(token in stripped.lower() for token in ("password", "secret", "api_key")) and "=" in stripped:
                issues.append(
                    {
                        "severity": "high" if analysis_mode == "security" else "medium",
                        "line": line_number,
                        "category": "security",
                        "description": "Possible hardcoded secret or credential.",
                        "suggestion": "Move secrets to environment variables or a secrets manager.",
                    }
                )
            if "except:" in stripped:
                issues.append(
                    {
                        "severity": "medium",
                        "line": line_number,
                        "category": "bug",
                        "description": "Bare except blocks can hide real failures.",
                        "suggestion": "Catch specific exceptions and handle them explicitly.",
                    }
                )
            if "print(" in stripped and analysis_mode == "general":
                issues.append(
                    {
                        "severity": "low",
                        "line": line_number,
                        "category": "style",
                        "description": "Debug printing should not remain in production code.",
                        "suggestion": "Replace print statements with structured logging.",
                    }
                )

        lower_code = code.lower()
        if "for " in lower_code and "while " in lower_code:
            issues.append(
                {
                    "severity": "medium",
                    "line": 1,
                    "category": "performance",
                    "description": "The code appears to contain multiple loop constructs that may affect performance.",
                    "suggestion": "Check whether repeated work can be moved out of loops or precomputed.",
                }
            )

        if not issues:
            suggestions.append("Add tests around edge cases and error handling.")
            suggestions.append("Extract repeated logic into helper functions.")
        else:
            suggestions.append("Address the highest-severity findings first.")
            suggestions.append("Add tests that cover the flagged lines and failure paths.")

        if analysis_mode == "security":
            summary = (
                f"This {language} code has a security-first review profile. "
                "The main risk areas are input handling, secrets management, and unsafe execution patterns. "
                "Tightening validation and removing risky constructs would improve its safety."
            )
        else:
            summary = (
                f"This {language} code is readable at a glance, but it has a few quality issues worth fixing. "
                "The review focuses on correctness, maintainability, and any obvious style or performance concerns. "
                "Small refactors and better tests would make it easier to evolve."
            )

        complexity = "high" if len(issues) >= 3 else "medium" if issues else "low"
        readability = "medium" if issues else "high"
        test_coverage_estimate = "low" if issues else "medium"

        return {
            "summary": summary,
            "issues": issues,
            "suggestions": suggestions,
            "metrics": {
                "complexity": complexity,
                "readability": readability,
                "test_coverage_estimate": test_coverage_estimate,
            },
        }


def create_default_client() -> AnalysisClient:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
    http_referer = os.getenv("OPENROUTER_HTTP_REFERER", "").strip() or None
    app_title = os.getenv("OPENROUTER_TITLE", "").strip() or None

    if api_key:
        return OpenAICompatibleClient(
            api_key=api_key,
            model=model,
            base_url=base_url,
            http_referer=http_referer,
            app_title=app_title,
        )
    return RuleBasedAnalysisClient()

