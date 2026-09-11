#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一键评审 git 改动，无需粘贴代码。

用法：
  python cli.py                      评审工作区未提交改动 (git diff)
  python cli.py --staged             评审已暂存改动 (git diff --cached)
  python cli.py --commit HEAD~1      评审最近一次提交的改动
  python cli.py --commit HEAD~3      评审最近 3 次提交的改动
  python cli.py src/utils.py         评审单个文件
  python cli.py --remote             用远程 Vercel 部署而非本地
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.request

REMOTE_URL = "https://code-review-agent-ashy-six.vercel.app"
LOCAL_URL = "http://127.0.0.1:8000"

_LANG_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "javascript",
    ".jsx": "javascript", ".tsx": "javascript",
    ".java": "java", ".go": "go", ".rs": "rust",
    ".rb": "ruby", ".php": "php", ".c": "c", ".cpp": "c",
    ".sh": "shell", ".bash": "shell",
}


def detect_lang(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    return _LANG_MAP.get(ext, "")


def run_git(*args) -> str:
    result = subprocess.run(
        ["git"] + list(args), capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode != 0:
        print(f"git 错误: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def get_diff(staged: bool, commit: str | None) -> str:
    if commit:
        return run_git("diff", commit)
    if staged:
        return run_git("diff", "--cached")
    return run_git("diff")


def call_api(base_url: str, endpoint: str, payload: dict) -> dict:
    url = base_url + endpoint
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"API 错误 {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"连接失败: {e}\n请先启动服务: uvicorn app.main:app", file=sys.stderr)
        sys.exit(1)


SEVERITY_ICON = {"critical": "🔴", "major": "🟠", "minor": "🟡", "info": "🔵"}
SOURCE_ICON = {"rule": "⚡", "llm": "🧠", "confirmed": "✅"}


def print_report(data: dict, is_diff: bool):
    if not data.get("ok"):
        print(f"❌ {data.get('error', '未知错误')}")
        return

    report = data.get("report", {})
    score = report.get("score", 0)
    grade = report.get("grade", "?")
    dims = report.get("dimension_scores", {})

    print(f"\n{'='*60}")
    print(f"  评分: {score}/100 ({grade}级)")
    if dims:
        dim_labels = {
            "correctness": "正确性", "security": "安全性",
            "performance": "性能", "maintainability": "可维护性",
            "best_practice": "最佳实践",
        }
        dim_str = "  ".join(f"{dim_labels[k]}:{v}" for k, v in dims.items() if k in dim_labels)
        print(f"  {dim_str}")

    if is_diff and "files_changed" in data:
        files = data.get("files_changed", [])
        print(f"  变更: {', '.join(files)}  +{data.get('added_lines',0)} -{data.get('removed_lines',0)}")

    info = report.get("engine_info", {})
    if info:
        print(f"  引擎: 规则{info.get('rule_count',0)} LLM{info.get('llm_count',0)} 确认{info.get('confirmed_count',0)}")

    print(f"{'='*60}\n")

    summary = report.get("summary", "")
    if summary:
        print(f"📋 {summary}\n")

    issues = report.get("issues", [])
    if not issues:
        print("✅ 未发现问题\n")
        return

    print(f"发现 {len(issues)} 个问题:\n")
    for i in issues:
        sev = i.get("severity", "info")
        src = i.get("source", "llm")
        line = f"行{i['line']}" if i.get("line") else "?"
        icon = SEVERITY_ICON.get(sev, "•")
        sicon = SOURCE_ICON.get(src, "")
        rule = f" [{i['rule_id']}]" if i.get("rule_id") else ""
        print(f"  {icon} {sicon} {i.get('title', '')} ({line}){rule}")
        print(f"     {i.get('description', '')[:120]}")
        if i.get("fix_code"):
            print(f"     🔧 修复: {i['fix_code'][:100]}")
        print()

    strengths = report.get("strengths", [])
    if strengths:
        print("👍 优点:")
        for s in strengths[:3]:
            print(f"  • {s}")
        print()


def main():
    parser = argparse.ArgumentParser(description="一键代码评审")
    parser.add_argument("--staged", action="store_true", help="评审已暂存改动")
    parser.add_argument("--commit", metavar="REF", help="评审指定提交的改动 (如 HEAD~1)")
    parser.add_argument("--remote", action="store_true", help="用远程 Vercel 部署")
    parser.add_argument("--url", metavar="URL", help="自定义 API 地址")
    parser.add_argument("file", nargs="?", help="评审单个文件")
    args = parser.parse_args()

    base = args.url or (REMOTE_URL if args.remote else LOCAL_URL)

    if args.file:
        if not os.path.exists(args.file):
            print(f"文件不存在: {args.file}", file=sys.stderr)
            sys.exit(1)
        code = open(args.file, "r", encoding="utf-8").read()
        lang = detect_lang(args.file)
        print(f"评审文件: {args.file} ({lang or '未知'})")
        data = call_api(base, "/v1/review", {"code": code, "language": lang})
        print_report(data, is_diff=False)
    else:
        diff = get_diff(args.staged, args.commit)
        if not diff.strip():
            print("没有检测到改动。")
            return
        line_count = diff.count("\n")
        print(f"评审 diff: {line_count} 行改动")
        data = call_api(base, "/v1/review_diff", {"diff": diff})
        print_report(data, is_diff=True)


if __name__ == "__main__":
    main()