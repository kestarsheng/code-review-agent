# -*- coding: utf-8 -*-
"""冒烟测试：调用评审引擎，验证 LLM 能正常返回结构化报告。

运行方式（PowerShell）：
    $env:LLM_API_KEY = "sk-你的DeepSeekKey"
    $env:LLM_BASE_URL = "https://api.deepseek.com/v1"
    $env:LLM_MODEL = "deepseek-chat"
    python smoke_test.py

预期输出：score / grade / issues 数量 / 前 3 条问题 / summary 摘要。
"""
from app.reviewer import review_code

code = (
    "def get_user(user_id):\n"
    '    query = f"SELECT * FROM users WHERE id = {user_id}"\n'
    "    return db.execute(query).fetchone()\n"
)

print("=== 待评审代码 ===")
print(code)
print("=== 调用评审引擎（DeepSeek）===\n")

r = review_code(code=code, language="python", context="用户查询接口")

print(f"score: {r.get('score')} | grade: {r.get('grade')}")
print(f"issues: {len(r.get('issues', []))} 条")
print("-" * 50)
for i in r.get("issues", []):
    print(f"  [{i.get('severity')}] {i.get('category')} - {i.get('title')}")
    if i.get("line"):
        print(f"    行 {i.get('line')}")
    print(f"    描述: {i.get('description')}")
    print(f"    建议: {i.get('suggestion')}")
    print()
print("-" * 50)
print(f"summary: {r.get('summary', '')}")
print(f"\nstrengths: {r.get('strengths', [])}")
print(f"improvements: {r.get('improvements', [])}")