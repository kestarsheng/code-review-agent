# -*- coding: utf-8 -*-
"""Core code review engine: calls an OpenAI-compatible LLM and returns a
structured JSON report."""
import json
import logging
import re
from typing import Any

from openai import OpenAI

from .config import get_settings
from .prompts import SYSTEM_PROMPT, build_user_prompt

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


def review_code(code: str, language: str = "", context: str = "") -> dict[str, Any]:
    """Run the code review against the configured LLM.

    Returns the raw dict from the model after basic validation.
    """
    settings = get_settings()
    if not settings.llm_api_key:
        raise ReviewError("LLM API Key 未配置（环境变量 LLM_API_KEY）")

    client = OpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        timeout=settings.llm_timeout_seconds,
    )
    user_prompt = build_user_prompt(language, context, code)

    try:
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
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