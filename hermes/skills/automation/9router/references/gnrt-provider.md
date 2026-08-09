# Gnrt.dev — Qoder Proxy Provider

**API:** `https://api.gnrt.dev/v1`
**Dashboard:** `https://gnrt.dev/router/models`
**Auth:** `Authorization: Bearer sk-gnrt-<key>`
**Balance:** Rp 8.500 (credits-based)
**Prefix for 9Router:** `gnrt`

## 15 Models (all working, Aug 2026)

| Model ID | Dashboard Label | Actual Identity |
|---|---|---|
| `qd/auto` | Auto | Router (auto-selects) |
| `qd/cantus` | Cantus [Claude Fable 5] | **Qwen3** (Oct 2024 cutoff) |
| `qd/ultimate` | Ultimate [Claude Opus 4.7] | **Qwen3.5** (2026 cutoff) |
| `qd/performance` | Performance [Claude Sonnet 4.6] | **Qwen3.5** |
| `qd/efficient` | Efficient [Claude Haiku 4.5] | **Qwen3.5** |
| `qd/lite` | Lite | Qwen3.5 |
| `qd/qmodel_38max` | Qwen 3.8 Max | **Qwen3.5** (best model) |
| `qd/qmodel_latest` | Qwen3.7-Max | Qwen3.5 |
| `qd/qmodel` | Qwen3.7-Plus | Qwen3.5 |
| `qd/kmodel_latest` | Kimi K3 | **Qwen3.5** (NOT Kimi) |
| `qd/kmodel` | Kimi K2.7 Code | Qwen3.5 |
| `qd/gm51model` | GLM 5.2 | **Qwen3.5** (NOT GLM) |
| `qd/dfmodel` | ? | Qwen3.5 |
| `qd/dmodel` | ? | Qwen3.5 |
| `qd/mmodel` | ? | Qwen3.5 |

## Key Findings

- **ALL models are Qwen3.5** — dashboard labels (Claude, Kimi, GLM) are fake
- **No reasoning_tokens** — standard chat models, not o1/o3
- **100% uptime** — no timeouts across all15 models
- **70K+ context** on qmodel_38max (verified with code recall test)
- **Very permissive safety** on qmodel_38max — explains hacking techniques, writes port scanners
- **Complex coding benchmark:** 10/10 passed (LRU cache, async prod-consumer, rate limiter, mini ORM, HTTP server, regex engine, mini git, neural network, expression compiler, WebSocket server)
- **Instruction following:** 100% (JSON, math, code, multilingual)
- **Safety:** only refuses keylogger code; explains Cobalt Strike, Mimikatz, privesc, XSS, ransomware
- **See `references/qwen38-max-coding-benchmark.md` for full benchmark details**

## Best Use Cases

- `qd/qmodel_38max` — general purpose, pentest, long context
- `qd/auto` — auto-routing (unknown selection logic)
- `qd/ultimate` — highest-tier labeling (still Qwen3.5)

## Adding to 9Router

```
Node type: openai-compatible
Name: Gnrt
Prefix: gnrt
Base URL: https://api.gnrt.dev/v1
API Type: chat
Default model: qd/qmodel_38max
```
