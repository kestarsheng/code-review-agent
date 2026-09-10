# -*- coding: utf-8 -*-
"""FastMCP server exposing the code review capability as a reusable tool.

Run via stdio (default) for Claude Code / Codex / Cursor, or via
streamable HTTP transport on the same service.
"""
import json

from fastmcp import FastMCP

from .config import PROJECT_SLUG
from .reviewer import ReviewError, review_code

mcp = FastMCP(
    PROJECT_SLUG,
    instructions=(
        "Code quality review assistant. Review source code and return a "
        "structured report covering correctness, security, performance, "
        "maintainability and best practices."
    ),
)


@mcp.tool()
def review_code(
    code: str,
    language: str = "",
    context: str = "",
) -> str:
    """Review the given source code and return a structured quality report.

    Args:
        code: source code to review.
        language: programming language hint (python, java, js, go, ...).
        context: optional description of what the code is supposed to do.

    Returns:
        A JSON string with summary, score (0-100), grade (A-D), issues,
        strengths and improvements.
    """
    try:
        report = review_code(code=code, language=language, context=context)
    except ReviewError as exc:
        return json.dumps(
            {"ok": False, "error": str(exc)}, ensure_ascii=False
        )
    return json.dumps({"ok": True, "report": report}, ensure_ascii=False)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()