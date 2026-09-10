# -*- coding: utf-8 -*-
"""Pydantic schemas for the code review service."""
from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["critical", "major", "minor", "info"]
Category = Literal[
    "correctness", "security", "performance", "maintainability", "best_practice"
]


class ReviewRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Source code to review")
    language: str = Field(
        default="", description="Programming language hint, e.g. python, java, js"
    )
    context: str = Field(
        default="", max_length=2000, description="Optional task/context description"
    )


class ReviewIssue(BaseModel):
    severity: Severity
    category: Category
    line: int | None = Field(
        default=None, description="Approximate 1-based line number, null if unknown"
    )
    title: str
    description: str
    suggestion: str


class ReviewReport(BaseModel):
    summary: str = Field(..., description="One-paragraph overall summary")
    score: int = Field(..., ge=0, le=100)
    grade: str = Field(..., description="A/B/C/D derived from score")
    issues: list[ReviewIssue]
    strengths: list[str]
    improvements: list[str]


class ReviewResponse(BaseModel):
    ok: bool = True
    language: str
    model: str
    report: ReviewReport


class HealthResponse(BaseModel):
    status: str
    commit: str


class VerificationResponse(BaseModel):
    schemaVersion: int
    slug: str
    commit: str