# Code Review Agent

AI 代码质量评审服务（Code Review as a Service）。把代码送给 LLM，返回结构化质量报告，亦可作为 MCP 工具被 Claude Code / Codex / Cursor 等 Agent 调用。

> Submission for **X-Agent AI MCP Hackathon 2026 · Open Innovation Challenge**.

## What it does

- `POST /v1/review` — 提交代码片段，返回结构化评审报告（正确性 / 安全 / 性能 / 可维护性 / 最佳实践）
- `GET /health` — 健康检查，返回当前部署 Commit
- `GET /.well-known/xagent-verification.json` — 部署证明（slug + commit）
- `GET /` — 在线演示页（粘贴代码即时出报告）
- MCP 工具 `review_code` — 供 Agent 调用（stdio / streamable HTTP）

## Quick start (local)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # 填入 LLM_API_KEY 等
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 (demo page) or http://127.0.0.1:8000/docs (Swagger).

Example call:

```bash
curl -X POST http://127.0.0.1:8000/v1/review \
  -H "Content-Type: application/json" \
  -d '{"code": "def foo(a, b):\n    return a / b", "language": "python"}'
```

## MCP usage

```bash
python -m app.mcp_server          # stdio transport for Claude Code / Codex / Cursor
```

Or register in your client config:

```json
{
  "mcpServers": {
    "code-review-agent": {
      "command": "python",
      "args": ["-m", "app.mcp_server"]
    }
  }
}
```

## Configuration (env vars)

| Var | Default | Description |
| --- | --- | --- |
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | OpenAI-compatible base URL |
| `LLM_API_KEY` | — | API key (required) |
| `LLM_MODEL` | `deepseek-chat` | Model name |
| `LLM_TIMEOUT_SECONDS` | `120` | LLM request timeout |
| `COMMIT` | `dev` | Deployed commit, returned by /health and /.well-known/xagent-verification.json |

## Deployment

- Docker: `docker build -t code-review-agent . && docker run -p 8000:8000 code-review-agent`
- Render: push to repo, set env vars, use `render.yaml` — set `COMMIT` to the exact deployed commit.

After deploy, verify:

```bash
curl https://<your-host>/health
curl https://<your-host>/.well-known/xagent-verification.json
```

## License

UNLICENSED — submission-only use for X-Agent AI MCP Hackathon 2026.