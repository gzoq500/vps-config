# b.ai Provider Reference

**API:** `https://api.b.ai/v1`
**Docs:** `https://docs.b.ai/llmservice/introduction`
**Key format:** `sk-*`
**Credit system:** 1 USD = 1,000,000 Credits
**New user gift:** 300,000 Credits (30 days, via invitation)

## Free Models (no deposit required)

| Model | Real Identity | Type | Notes |
|---|---|---|---|
| `qwen3.6-27b` | Qwen3.6-27B-FP8 (Alibaba) | Standard LLM | Cutoff 2026, no reasoning tokens |
| `kimi-k2.5` | Kimi K2.5 (Moonshot AI) | Reasoning | ~299 reasoning tokens, content empty at low max_tokens |
| `minimax-m2.7` | MiniMax-M2.7 | Thinking | Has `<think>` tags in content |

## Premium Models (deposit required)

38 total models including: qwen3.8-max, claude-opus-5, gpt-5.2/5.4/5.5/5.6, gemini-3.x, kimi-k2.6/k3, deepseek-v4, glm-5.x, minimax-m3. All return `access_denied` without deposit.

## Key Differences: API vs Chat App

The BAI Chat App and API key have DIFFERENT access levels:
- **Chat App:** Uses free registration credits, can access premium models (e.g. Qwen3.8-Max with Deep Thinking)
- **API key:** Returns `access_denied` for premium models without deposit

The chat app shows "Deep Thinking" indicator with reasoning time and token count (e.g. "✦3,150" tokens).

## Authentication

```bash
curl -s https://api.b.ai/v1/chat/completions \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.6-27b","messages":[{"role":"user","content":"Hi"}],"max_tokens":50}'
```

## Billing Endpoint (restricted)

`/v1/dashboard/billing/usage` returns HTTP-only path restriction. Only these paths work via API:
- `/v1/chat/completions`
- `/v1/messages`
- `/v1/responses`
- `/v1/models`
- `/v1/images/*`

## Model Response Format

Standard OpenAI chat completions format. No `reasoning_content` field in response (reasoning appears in `<think>` tags for MiniMax, or in `reasoning_content` for Kimi K2.5).

```json
{
  "id": "chatcmpl-...",
  "model": "Qwen/Qwen3.6-27B-FP8",  // Real model name, not the alias
  "choices": [{"message": {"content": "..."}}],
  "usage": {"prompt_tokens": ..., "completion_tokens": ..., "total_tokens": ...}
}
```

## 9Router Integration

Prefix: `bai`
Base URL: `https://api.b.ai/v1`
API Type: Chat Completions
Default model: `qwen3.6-27b`

## Testing Notes (Aug 2026)

- All 3 free models verified authentic via self-identification
- `qwen3.6-27b`: Fast, reliable, good general-purpose
- `kimi-k2.5`: Needs `max_tokens:200+` for content (reasoning consumes budget)
- `minimax-m2.7`: Shows thinking process in output
- Rate limits not observed on free models
- No vision support confirmed on free models
