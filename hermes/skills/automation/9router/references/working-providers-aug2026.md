# Working 9Router Providers (Aug 2026)

## Provider Summary

| Provider | Prefix | Base URL | Models | Status |
|---|---|---|---|---|
| XKiro | `xkiro` | `api.xkiro.com/v1` | 66 listed, free=2 text-only | ⚠️ Free plan blocks vision |
| GoRouter | `gorouter` | `gorouter.app/v1` | 4 Claude models | ✅ Paid |
| OrcaRouter | `orca` | `api.orcarouter.ai/v1` | 1 (tencent/hy3) | ✅ Free text only |
| MiMo (Xiaomi) | `mimo` | `api.xiaomimimo.com/v1` | 2 (mimo-v2.5, pro) | ✅ Chat, no vision |
| SeekAI | `seekai` | `seekai.cc/v1` | 19 listed, ~9 work | ⚠️ Free, unstable |
| HCNSEC | `hcnsec` | `api.hcnsec.cn/v1` | 21 listed, ~8 work | ⚠️ Routing mismatch |
| Aerolink | `aerolink` | `cgapi.aerolink.lat/v1` | 3 (gpt-5.6-*) | ✅ Responses API |
| RoutLLM | `routllm` | `routllm.pro/v1` | 11 listed, all fail | ❌ 502/403 |
| OneRouter | — | `llm.onerouter.pro/v1` | 458 listed | ❌ Credits required |
| Qoder | — | `openapi.qoder.sh` | IDE only | ❌ No REST API |

## Key Rotation Notes

- **XKiro free models (Aug 2026):** `deepseek/deepseek-v4-flash`, `mistralai/ministral-3b` only. All mimo/vision models are premium.
- **MiMo built-in provider:** 9Router has built-in `xiaomi-mimo` provider. Prefix `mimo` and `xiaomi-mimo` both work. Connections use `provider: 'xiaomi-mimo'` (name string, NOT UUID).
- **HCNSEC routing:** `DeepSeek-V4-Pro` → Nemotron (wrong!), `Qwen3.5` → xopqwen (wrong!). Always verify `model` field in response.
- **Aerolink identity:** Models claim "ChatGPT, cutoff June 2024" with reasoning_tokens. Likely o1/o3-mini rebranded as GPT-5.6. Luna=least filtered, Sol=most filtered, Terra=mid. See `aerolink-deep-fingerprint.md`.
- **SeekAI stability:** `/v1/models` returns instantly but `/v1/chat/completions` returns 500 for all models (upstream down). Always test chat before relying.
- **RoutLLM free plan:** Covers Gemini only. All Gemini models 502 (upstream down). Non-Gemini requires paid plan. $33.62 balance exists but can't be used on free tier.
- **OneRouter:** Free models with `:free` suffix require >$5 balance. Only3 models work free: `inclusionai/ling-3.0-flash:free`, `poolside/laguna-s-2.1:free`, `mindai/macaron-v1-venti:free`.
- **Qoder:** PAT→job token exchange works. 300 credits + 800 Qwen3.8-Max calls available. But API is IDE-only — no `/v1/chat/completions` endpoint. Use via Qoder Desktop/CLI only.

## Buffalo VPS (209.127.114.234) — Current Setup

9Router on port **20128** (systemd auto-restart). Vision through9Router:
```yaml
auxiliary:
  vision:
    provider: custom
    model: mimo/mimo-v2.5
    base_url: http://209.127.114.234:20128/v1
    api_key: YOUR_9ROUTER_KEY
```

Built-in connections: `2E3U84` (#1) and `8EJPG2` (#2) on `xiaomi-mimo` provider.
