# -*- coding: utf-8 -*-
"""Prompt templates for the dual-engine code review system."""

SYSTEM_PROMPT = """\
你是一名资深软件架构师与代码评审专家，擅长从正确性、安全性、性能、\
可维护性和最佳实践五个维度评审代码。你输出的评审结论必须基于代码事实，\
不得臆造。请以严格的 JSON 格式输出评审报告，不要输出任何 JSON 以外的内容。
"""

SYSTEM_PROMPT_WITH_RULES = """\
你是一名资深软件架构师与代码评审专家。你正在与一个规则引擎协同工作——\
规则引擎已通过静态模式匹配发现了若干已知问题（见下方"规则引擎预检结果"）。\
你的任务是：
1. 确认或否定规则引擎的发现（若规则误报请在 issues 中说明）
2. 发现规则引擎无法检测的语义问题（逻辑错误、架构缺陷、业务逻辑等）
3. 从正确性、安全性、性能、可维护性、最佳实践五个维度综合评审

你输出的评审结论必须基于代码事实，不得臆造。\
请以严格的 JSON 格式输出评审报告，不要输出任何 JSON 以外的内容。
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
      "category": "correctness 或 security 或 performance 或 maintainability 或 best_practice 或 ai_pattern",
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
4. 若规则引擎预检结果中存在误报，请在 issues 中用 severity=info 说明"规则引擎 XX 为误报"。
"""

DIFF_SYSTEM_PROMPT = """\
你是一名资深代码评审专家，正在评审一个代码变更（diff）。\
请重点关注变更部分的风险：是否引入安全漏洞、是否破坏现有逻辑、\
是否有性能退化、变更是否完整（如新增分支但未处理所有路径）。\
请以严格的 JSON 格式输出评审报告，不要输出任何 JSON 以外的内容。
"""


def build_user_prompt(language: str, context: str, code: str) -> str:
    parts = [f"语言：{language or '未知'}"]
    if context:
        parts.append(f"任务上下文：{context}")
    parts.append("待评审代码：")
    parts.append("```" + language + "\n" + code + "\n```")
    parts.append(JSON_SCHEMA_EXAMPLE)
    return "\n".join(parts)


def build_user_prompt_with_rules(
    language: str,
    context: str,
    code: str,
    rule_findings: list[dict],
) -> str:
    """Build prompt that includes rule engine pre-check results for LLM."""
    parts = [f"语言：{language or '未知'}"]
    if context:
        parts.append(f"任务上下文：{context}")

    if rule_findings:
        parts.append("规则引擎预检结果：")
        for f in rule_findings:
            parts.append(
                f"  [{f['rule_id']}] {f['severity']}/{f['category']} "
                f"行{f.get('line', '?')}: {f['title']}"
            )
        parts.append("")
    else:
        parts.append("规则引擎预检结果：未发现已知模式问题。\n")

    parts.append("待评审代码：")
    parts.append("```" + language + "\n" + code + "\n```")
    parts.append(JSON_SCHEMA_EXAMPLE)
    return "\n".join(parts)


def build_diff_prompt(language: str, context: str, diff: str, diff_meta: str) -> str:
    """Build prompt for diff-level review."""
    parts = [f"语言：{language or '未知'}"]
    if context:
        parts.append(f"任务上下文：{context}")
    parts.append(f"变更概要：{diff_meta}")
    parts.append("待评审 diff：")
    parts.append("```diff\n" + diff + "\n```")
    parts.append(JSON_SCHEMA_EXAMPLE)
    return "\n".join(parts)
