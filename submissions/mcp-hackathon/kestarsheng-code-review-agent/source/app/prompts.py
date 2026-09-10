# -*- coding: utf-8 -*-
"""Prompt templates for the code review engine."""

SYSTEM_PROMPT = """\
你是一名资深软件架构师与代码评审专家，擅长从正确性、安全性、性能、\
可维护性和最佳实践五个维度评审代码。你输出的评审结论必须基于代码事实，\
不得臆造。请以严格的 JSON 格式输出评审报告，不要输出任何 JSON 以外的内容。
"""

JSON_SCHEMA_EXAMPLE = """\
评审报告 JSON 结构如下：
{
  "summary": "一段 2-4 句的总体评价，指出最关键的问题与整体质量",
  "score": 0到100的整数,
  "grade": "由 score 派生，90-100 为 A，75-89 为 B，60-74 为 C，60 以下为 D",
  "issues": [
    {
      "severity": "critical 或 major 或 minor 或 info",
      "category": "correctness 或 security 或 performance 或 maintainability 或 best_practice",
      "line": 问题所在的大致行号(1-based)，无法确定时填 null,
      "title": "一句话问题标题",
      "description": "问题详细描述，说明为什么是问题、可能后果",
      "suggestion": "具体可行的修复建议，尽量给出示例代码"
    }
  ],
  "strengths": ["代码优点列表，至少 1 条"],
  "improvements": ["改进方向列表，至少 1 条"]
}

规则：
1. issues 中必须至少包含一条真正存在的问题；若确实没有问题，severity 用 info 说明代码状态优秀。
2. 不要编造代码中不存在的问题。security 类别优先于其他类别报告。
3. 建议要具体、可执行，需要时可附简短示例代码。
"""


def build_user_prompt(language: str, context: str, code: str) -> str:
    parts = [f"语言：{language or '未知'}"]
    if context:
        parts.append(f"任务上下文：{context}")
    parts.append("待评审代码：")
    parts.append("```" + language + "\n" + code + "\n```")
    parts.append(JSON_SCHEMA_EXAMPLE)
    return "\n".join(parts)