# -*- coding: utf-8 -*-
"""Unit tests for the dual-engine code review service."""
import json

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.diff_parser import parse_diff
from app.main import app
from app.reviewer import _extract_json
from app.rules_engine import detect_language, merge_findings, run_rules

client = TestClient(app)


# ── Meta endpoints ──────────────────────────────────────────────

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


# ── Rule engine ─────────────────────────────────────────────────

def test_rules_detect_eval():
    code = "result = eval(user_input)"
    findings = run_rules(code, "python")
    ids = [f.rule_id for f in findings]
    assert "PY-S001" in ids


def test_rules_detect_hardcoded_secret():
    code = 'api_key = "sk-1234567890abcdef"'
    findings = run_rules(code, "python")
    ids = [f.rule_id for f in findings]
    assert "PY-S004" in ids


def test_rules_detect_sql_injection():
    code = 'cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")'
    findings = run_rules(code, "python")
    ids = [f.rule_id for f in findings]
    assert "PY-S006" in ids


def test_rules_detect_js_innerhtml():
    code = "document.getElementById('x').innerHTML = userInput"
    findings = run_rules(code, "javascript")
    ids = [f.rule_id for f in findings]
    assert "JS-S002" in ids


def test_rules_detect_todo():
    code = "# TODO: fix this later\npass"
    findings = run_rules(code, "python")
    ids = [f.rule_id for f in findings]
    assert "X-M001" in ids


def test_rules_clean_code_no_findings():
    code = "def add(a: int, b: int) -> int:\n    return a + b"
    findings = run_rules(code, "python")
    security = [f for f in findings if f.severity == "critical"]
    assert len(security) == 0


def test_detect_language_python():
    assert detect_language("def foo():\n    pass", "python") == "python"
    assert detect_language("def foo():\n    pass", "") == "python"


def test_detect_language_javascript():
    assert detect_language("const x = 1", "js") == "javascript"
    assert detect_language("const x = 1", "") == "javascript"


def test_detect_language_java():
    assert detect_language("import java.util.List;", "") == "java"


def test_detect_language_go():
    assert detect_language("func main() {\n}", "") == "go"


def test_merge_findings_rule_only():
    rule_findings = run_rules("eval('1+1')", "python")
    merged = merge_findings(rule_findings, [], "eval('1+1')")
    assert any(m["source"] == "rule" for m in merged)


def test_merge_findings_confirmed():
    rule_findings = run_rules("eval('1+1')", "python")
    llm_issues = [
        {"severity": "critical", "category": "security", "line": 1,
         "title": "eval", "description": "RCE", "suggestion": "don't use eval"}
    ]
    merged = merge_findings(rule_findings, llm_issues, "eval('1+1')")
    assert any(m["source"] == "confirmed" for m in merged)


def test_list_rules_endpoint():
    resp = client.get("/v1/rules")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] > 10
    assert any(r["id"] == "PY-S001" for r in body["rules"])


# ── Diff parser ─────────────────────────────────────────────────

def test_parse_simple_diff():
    diff = """--- a/foo.py
+++ b/foo.py
@@ -1,3 +1,4 @@
 def foo():
-    return 1
+    return 2
+    pass
"""
    parsed = parse_diff(diff)
    assert "foo.py" in parsed.files_changed
    assert parsed.added_lines == 2
    assert parsed.removed_lines == 1
    assert len(parsed.hunks) == 1


def test_parse_empty_diff():
    parsed = parse_diff("")
    assert len(parsed.hunks) == 0
    assert parsed.added_lines == 0


# ── Review API ──────────────────────────────────────────────────

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


def test_review_diff_requires_body():
    resp = client.post("/v1/review_diff", json={})
    assert resp.status_code == 422


# ── JSON extraction ─────────────────────────────────────────────

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
