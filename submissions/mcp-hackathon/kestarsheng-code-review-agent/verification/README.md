# Verification evidence

## Prerequisites

- Review commit: `f28109a1754b2a0811262dd11b97e0ec361eddb7`
- API base URL: `__API_BASE_URL__/v1`
- Authentication: none

## 1. Health check

```bash
curl --fail --silent --show-error __API_BASE_URL__/health
```

Expected response:

```json
{"status":"ok","commit":"f28109a1754b2a0811262dd11b97e0ec361eddb7"}
```

## 2. Deployment proof

```bash
curl --fail --silent --show-error __API_BASE_URL__/.well-known/xagent-verification.json
```

Expected response:

```json
{"schemaVersion":1,"slug":"kestarsheng-code-review-agent","commit":"f28109a1754b2a0811262dd11b97e0ec361eddb7"}
```

## 3. Capability call

```bash
curl --fail --silent --show-error \
  --request POST __API_BASE_URL__/v1/review \
  --header "content-type: application/json" \
  --data '{"code":"def f(x):\n    return x / 0","language":"python"}'
```

Expected success response (abridged):

```json
{
  "ok": true,
  "language": "python",
  "model": "deepseek-chat",
  "report": {
    "summary": "...",
    "score": 30,
    "grade": "D",
    "issues": [
      {
        "severity": "critical",
        "category": "correctness",
        "line": 2,
        "title": "除零错误",
        "description": "...",
        "suggestion": "..."
      }
    ],
    "strengths": ["..."],
    "improvements": ["..."]
  }
}
```

## 4. Safe error behavior

Empty body:

```bash
curl --fail --silent --show-error \
  --request POST __API_BASE_URL__/v1/review \
  --header "content-type: application/json" \
  --data '{}'
```

Expected: HTTP 422 with `{"ok":false,"error":...}`.

Oversized code (> 60 000 chars): HTTP 413.
LLM provider failure: HTTP 502 with `{"ok":false,"error":"LLM 调用失败: ..."}`.