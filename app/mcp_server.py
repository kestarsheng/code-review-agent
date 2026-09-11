# -*- coding: utf-8 -*-
"""FastMCP server exposing code review capabilities as reusable MCP tools.

Tools:
- review_code:    dual-engine review of a source code snippet
- review_diff:    dual-engine review of a unified diff / PR change
- detect_security: fast rule-only security scan (no LLM, instant)
- list_rules:     list all built-in rule engine rules

Run via stdio (default) for Claude Code / Codex / Cursor.
"""
import json

from fastmcp import FastMCP

from .config import PROJECT_SLUG
from .reviewer import (
    ReviewError,
    explain_issue,
    review_code,
    review_diff,
    review_files,
    suggest_fix_for_code,
)
from .rules_engine import RULES, run_rules

mcp = FastMCP(
    PROJECT_SLUG,
    instructions=(
        "Dual-engine code review assistant. Combines a rule-based static "
        "analysis engine with LLM semantic review for cross-validated "
        "quality reports. Tools: review_code, review_diff, review_files, "
        "detect_security, explain_issue, suggest_fix, list_rules."
    ),
)


@mcp.tool()
def review_code_tool(
    code: str,
    language: str = "",
    context: str = "",
) -> str:
    """Review source code with dual-engine (rules + LLM) and return a structured report.

    Args:
        code: source code to review.
        language: programming language hint (python, java, js, go, ...).
        context: optional description of what the code is supposed to do.

    Returns:
        JSON string with summary, score, grade, issues (with source attribution),
        strengths, improvements, and engine_info.
    """
    try:
        report = review_code(code=code, language=language, context=context)
    except ReviewError as exc:
        return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
    return json.dumps({"ok": True, "report": report}, ensure_ascii=False)


@mcp.tool()
def review_diff_tool(
    diff: str,
    language: str = "",
    context: str = "",
) -> str:
    """Review a unified diff (e.g. git diff output) for change-level risks.

    Args:
        diff: unified diff text.
        language: programming language hint.
        context: optional description of the change purpose.

    Returns:
        JSON string with diff metadata and a structured review report.
    """
    try:
        result = review_diff(diff=diff, language=language, context=context)
    except ReviewError as exc:
        return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
    return json.dumps({"ok": True, "result": result}, ensure_ascii=False)


@mcp.tool()
def review_files_tool(
    files: str,
    context: str = "",
) -> str:
    """Review multiple files (JSON array) with dual-engine analysis.

    Args:
        files: JSON array string of objects, each {filename, content, language?}.
        context: optional project/task context description.

    Returns:
        JSON string with per-file reports and an overall cross-file report.
    """
    try:
        parsed_files = json.loads(files)
        if not isinstance(parsed_files, list) or not parsed_files:
            return json.dumps(
                {"ok": False, "error": "files 必须是包含文件的 JSON 数组"},
                ensure_ascii=False,
            )
        result = review_files(files=parsed_files, context=context)
    except (json.JSONDecodeError, KeyError) as exc:
        return json.dumps(
            {"ok": False, "error": f"files 参数解析失败: {exc}"}, ensure_ascii=False
        )
    except ReviewError as exc:
        return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
    return json.dumps({"ok": True, "result": result}, ensure_ascii=False)


@mcp.tool()
def explain_issue(rule_id: str) -> str:
    """Explain a rule-engine rule in detail (no LLM call, instant).

    Args:
        rule_id: rule ID, e.g. PY-S001, JS-S002, AI-H003.

    Returns:
        JSON string with rule definition, severity, category and guidance.
    """
    result = explain_issue(rule_id)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def suggest_fix(
    code: str,
    language: str = "",
    context: str = "",
) -> str:
    """Generate a full corrected version of code with known issues (LLM).

    Rules engine runs first to surface deterministic findings, then the LLM
    produces a complete fixed_code block that can replace the original.

    Args:
        code: source code to fix.
        language: programming language hint (python, java, js, go, ...).
        context: optional description of what the code is supposed to do.

    Returns:
        JSON string with fixed_code, explanation, and list of changes.
    """
    try:
        result = suggest_fix_for_code(code=code, language=language, context=context)
    except ReviewError as exc:
        return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
    return json.dumps({"ok": True, "result": result}, ensure_ascii=False)


@mcp.tool()
def detect_security(code: str, language: str = "") -> str:
    """Fast rule-only security scan — no LLM call, returns instantly.

    Args:
        code: source code to scan.
        language: programming language hint.

    Returns:
        JSON string with detected security issues and their rule IDs.
    """
    findings = run_rules(code, language)
    security_findings = [
        f for f in findings if f.category in ("security", "ai_pattern")
    ]
    return json.dumps(
        {
            "ok": True,
            "total_findings": len(security_findings),
            "findings": [
                {
                    "rule_id": f.rule_id,
                    "severity": f.severity,
                    "category": f.category,
                    "line": f.line,
                    "title": f.title,
                    "description": f.description,
                    "suggestion": f.suggestion,
                    "confidence": f.confidence,
                }
                for f in security_findings
            ],
        },
        ensure_ascii=False,
    )


@mcp.tool()
def list_rules() -> str:
    """List all built-in rule engine rules with their metadata.

    Returns:
        JSON string with all rules (id, language, severity, category, title).
    """
    return json.dumps(
        {
            "total": len(RULES),
            "rules": [
                {
                    "id": r.id,
                    "language": r.language,
                    "severity": r.severity,
                    "category": r.category,
                    "confidence": r.confidence,
                    "title": r.title,
                }
                for r in RULES
            ],
        },
        ensure_ascii=False,
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
