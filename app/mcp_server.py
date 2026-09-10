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
from .reviewer import ReviewError, review_code, review_diff
from .rules_engine import RULES, run_rules

mcp = FastMCP(
    PROJECT_SLUG,
    instructions=(
        "Dual-engine code review assistant. Combines a rule-based static "
        "analysis engine with LLM semantic review for cross-validated "
        "quality reports. Tools: review_code, review_diff, "
        "detect_security, list_rules."
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
