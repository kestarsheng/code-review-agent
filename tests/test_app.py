# -*- coding: utf-8 -*-
"""Unit tests for the code review service."""
import json

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.reviewer import _extract_json

client = TestClient(app)


def test_health_returns_commit():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["commit"] == get_settings().commit


def test_verification_well_known():
    resp = client.get("/.well-known/xagent-verification.json")
    assert resp.status_code == 200
    body = resp.json()
    assert body["schemaVersion"] == 1
    assert body["slug"] == "kestarsheng-code-review-agent"
    assert "commit" in body


def test_review_requires_body():
    resp = client.post("/v1/review", json={})
    assert resp.status_code == 422


def test_review_validates_max_length(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "max_code_chars", 10)
    resp = client.post(
        "/v1/review",
        json={"code": "x" * 100, "language": "python"},
    )
    assert resp.status_code == 413


def test_review_reports_llm_error(monkeypatch):
    from app import main as main_module
    from app.reviewer import ReviewError

    def fake_review(*args, **kwargs):
        raise ReviewError("LLM API Key 未配置")

    monkeypatch.setattr(main_module, "review_code", fake_review)
    resp = client.post(
        "/v1/review",
        json={"code": "print(1)", "language": "python"},
    )
    assert resp.status_code == 502
    assert "LLM API Key 未配置" in resp.text


def test_extract_json_fenced():
    text = '```json\n{"issues": [], "score": 80, "summary": "ok"}\n```'
    data = _extract_json(text)
    assert data["score"] == 80


def test_extract_json_embedded():
    text = '说明如下：{"issues": [], "score": 90, "summary": "good"} 结束'
    data = _extract_json(text)
    assert data["score"] == 90


def test_extract_json_invalid():
    from app.reviewer import ReviewError

    with pytest.raises(ReviewError):
        _extract_json("完全没有JSON")