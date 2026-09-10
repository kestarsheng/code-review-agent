# -*- coding: utf-8 -*-
"""Dual-engine code review: rule-based static analysis + LLM semantic review.

The rule engine runs first (fast, deterministic, no API cost), detecting
known anti-patterns. The LLM then reviews the code with awareness of rule
findings, adding semantic analysis and confirming/denying rule hits.

Results are merged with source attribution:
- "rule": found by rule engine only
- "llm": found by LLM only
- "confirmed": both engines agree (highest confidence)
"""
import json
import logging
import re
from typing import Any

from openai import OpenAI

from .config import get_settings
from .diff_parser import diff_summary, parse_diff
from .prompts import (
    DIFF_SYSTEM_PROMPT,
    SYSTEM_PROMPT_WITH_RULES,
    build_diff_prompt,
    build_user_prompt,
    build_user_prompt_with_rules,
)
from .rules_engine import merge_findings, run_rules

logger = logging.getLogger(__name__)


class ReviewError(Exception):
    pass


def _extract_json(text: str) -> dict[str, Any]:
    """Extract the first JSON object from a model response (tolerates fences)."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ReviewError("模型未返回有效 JSON")
        return json.loads(match.group(0))


def _call_llm(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    """Call the configured LLM and return parsed JSON."""
    settings = get_settings()
    if not settings.llm_api_key:
        raise ReviewError("LLM API Key 未配置（环境变量 LLM_API_KEY）")

    client = OpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        timeout=settings.llm_timeout_seconds,
    )

    try:
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=4000,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("LLM call failed")
        raise ReviewError(f"LLM 调用失败: {exc}") from exc

    content = resp.choices[0].message.content or "{}"
    data = _extract_json(content)

    if not isinstance(data, dict) or "issues" not in data:
        raise ReviewError("模型返回结构不完整，缺少 issues 字段")
    return data


def review_code(code: str, language: str = "", context: str = "") -> dict[str, Any]:
    """Run dual-engine review: rules first, then LLM with rule context.

    Returns a structured report with merged findings and engine metadata.
    """
    # ── Phase 1: Rule engine (fast, local, no API cost) ──
    rule_findings = run_rules(code, language)
    rule_dicts = [
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
        for f in rule_findings
    ]
    logger.info("Rule engine found %d issues", len(rule_findings))

    # ── Phase 2: LLM review with rule context ──
    user_prompt = build_user_prompt_with_rules(language, context, code, rule_dicts)
    llm_data = _call_llm(SYSTEM_PROMPT_WITH_RULES, user_prompt)
    llm_issues = llm_data.get("issues", [])

    # ── Phase 3: Merge and attribute ──
    merged_issues = merge_findings(rule_findings, llm_issues, code)

    rule_count = sum(1 for i in merged_issues if i.get("source") == "rule")
    llm_count = sum(1 for i in merged_issues if i.get("source") == "llm")
    confirmed_count = sum(1 for i in merged_issues if i.get("source") == "confirmed")

    report = {
        "summary": llm_data.get("summary", ""),
        "score": llm_data.get("score", 50),
        "grade": llm_data.get("grade", "C"),
        "issues": merged_issues,
        "strengths": llm_data.get("strengths", []),
        "improvements": llm_data.get("improvements", []),
        "engine_info": {
            "rule_count": rule_count,
            "llm_count": llm_count,
            "confirmed_count": confirmed_count,
            "total_rules_run": len(rule_findings),
            "engines": ["rule", "llm"],
        },
    }
    return report


def review_diff(diff: str, language: str = "", context: str = "") -> dict[str, Any]:
    """Review a unified diff: parse, reconstruct changed code, dual-engine review."""
    parsed = parse_diff(diff)
    if not parsed.reconstructed_code.strip():
        return {
            "summary": "变更不包含实质性代码修改（仅删除或空白变更）。",
            "score": 100,
            "grade": "A",
            "issues": [],
            "strengths": ["变更无引入新代码的风险"],
            "improvements": [],
            "engine_info": {
                "rule_count": 0,
                "llm_count": 0,
                "confirmed_count": 0,
                "total_rules_run": 0,
                "engines": ["rule", "llm"],
            },
            "diff_meta": {
                "files_changed": parsed.files_changed,
                "added_lines": parsed.added_lines,
                "removed_lines": parsed.removed_lines,
                "hunks": len(parsed.hunks),
            },
        }

    meta = diff_summary(parsed)
    rule_findings = run_rules(parsed.reconstructed_code, language)
    rule_dicts = [
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
        for f in rule_findings
    ]

    user_prompt = build_diff_prompt(language, context, diff, meta)
    llm_data = _call_llm(DIFF_SYSTEM_PROMPT, user_prompt)
    llm_issues = llm_data.get("issues", [])
    merged_issues = merge_findings(rule_findings, llm_issues, parsed.reconstructed_code)

    rule_count = sum(1 for i in merged_issues if i.get("source") == "rule")
    llm_count = sum(1 for i in merged_issues if i.get("source") == "llm")
    confirmed_count = sum(1 for i in merged_issues if i.get("source") == "confirmed")

    report = {
        "summary": llm_data.get("summary", ""),
        "score": llm_data.get("score", 50),
        "grade": llm_data.get("grade", "C"),
        "issues": merged_issues,
        "strengths": llm_data.get("strengths", []),
        "improvements": llm_data.get("improvements", []),
        "engine_info": {
            "rule_count": rule_count,
            "llm_count": llm_count,
            "confirmed_count": confirmed_count,
            "total_rules_run": len(rule_findings),
            "engines": ["rule", "llm"],
        },
        "diff_meta": {
            "files_changed": parsed.files_changed,
            "added_lines": parsed.added_lines,
            "removed_lines": parsed.removed_lines,
            "hunks": len(parsed.hunks),
        },
    }
    return report
