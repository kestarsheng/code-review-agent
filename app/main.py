# -*- coding: utf-8 -*-
"""FastAPI application entry point.

Provides:
- POST /v1/review            review source code and return a structured report
- GET  /health               health check returning the deployed commit
- GET  /.well-known/xagent-verification.json   deployment proof
- GET  /                     minimal web demo page
"""
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from .config import PROJECT_SLUG, get_settings
from .reviewer import ReviewError, review_code
from .schemas import (
    HealthResponse,
    ReviewRequest,
    ReviewResponse,
    VerificationResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
app = FastAPI(
    title="Code Review Agent",
    description="AI code quality review as a service. "
    "Send code, get a structured review report.",
    version="1.0.0",
)


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", commit=settings.commit)


@app.get(
    "/.well-known/xagent-verification.json",
    response_model=VerificationResponse,
    tags=["meta"],
)
def verification() -> VerificationResponse:
    return VerificationResponse(
        schemaVersion=1, slug=PROJECT_SLUG, commit=settings.commit
    )


@app.post("/v1/review", response_model=ReviewResponse, tags=["review"])
async def review(req: ReviewRequest) -> ReviewResponse:
    if len(req.code) > settings.max_code_chars:
        raise HTTPException(
            status_code=413,
            detail=f"code 过长（限制 {settings.max_code_chars} 字符）",
        )
    try:
        report = review_code(code=req.code, language=req.language, context=req.context)
    except ReviewError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ReviewResponse(language=req.language, model=settings.llm_model, report=report)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index() -> HTMLResponse:
    html = Path(__file__).resolve().parent.parent / "web" / "index.html"
    if html.exists():
        return HTMLResponse(html.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Code Review Agent</h1><p>See /docs for API.</p>")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"ok": False, "error": exc.detail},
    )


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    main()