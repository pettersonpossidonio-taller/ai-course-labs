from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Severity = Literal["high", "medium", "low"]
IssueCategory = Literal[
    "bug",
    "security",
    "performance",
    "style",
    "maintainability",
]
AnalysisMode = Literal["general", "security"]


class AnalyzeRequest(BaseModel):
    code: str = Field(min_length=1)
    language: str = Field(min_length=1)
    analysis_mode: AnalysisMode = "general"


class Issue(BaseModel):
    severity: Severity
    line: int = Field(ge=1)
    category: IssueCategory
    description: str = Field(min_length=1)
    suggestion: str = Field(min_length=1)


class Metrics(BaseModel):
    complexity: str = Field(min_length=1)
    readability: str = Field(min_length=1)
    test_coverage_estimate: str = Field(min_length=1)


class AnalyzeResponse(BaseModel):
    summary: str = Field(min_length=1)
    issues: list[Issue]
    suggestions: list[str]
    metrics: Metrics

