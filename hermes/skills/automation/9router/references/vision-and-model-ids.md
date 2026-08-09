# 9Router — Vision & Model ID Reference

Updated 2026-07-27.

## CURRENT WORKING SETUP (proven)

**Chat:** `onerouter/qwen/qwen3.8-max-preview:free` via 9Router → OneRouter
**Vision:** `nvidia/nemotron-nano-12b-v2-vl:free` via OpenRouter DIRECT (bypasses 9Router)

Hermes config:
```yaml
auxiliary:
  vision:
    provider: custom
    model: nvidia/nemotron-nano-12b-v2-vl:free
    base_url: https://openrouter.ai/api/v1
    api_key: sk-or-v1-...
```

## OpenRouter FREE vision (recommended)

- **Model:** `nvidia/nemotron-nano-12b-v2-vl:free`
- **API:** `https://openrouter.ai/api/v1`
- **Cost:** $0, no balance needed
- **Works with:** base64 images (`data:image/png;base64,...`)
- **Issues:** External URLs may fail with Nvidia "thumbnail sizes" error. Use base64 or small images.
- **Latency:** ~5-30s for vision requests
- **Other free models (July 2026):** 15 total. Chat: `nvidia/nemotron-3-ultra-550b-a55b:free`, `google/gemma-4-31b-it:free`, `poolside/laguna-s-2.1:free`. Query `/api/v1/models` and filter `:free`.

### Quick vision test (OpenRouter direct)
```bash
curl -s --max-time 30 -X POST "https://openrouter.ai/api/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OR_KEY" \
  -d '{
    "model": "nvidia/nemotron-nano-12b-v2-vl:free",
    "messages": [{"role":"user","content":[
      {"type":"text","text":"What color is this?"},
      {"type":"image_url","image_url":{"url":"data:image/png;base64,<TINY_PNG>"}}
    ]}],
    "stream": false, "max_tokens": 20
  }'
```

## 9Router routing failure for new providers

**CRITICAL:** Adding providers via DB insert or even UI "Add API Key" form may NOT sync with the routing engine. Symptoms:
- UI shows "1 Connected", Test Connection passes
- API returns `No active credentials for provider: <prefix>`
- Multiple restarts don't fix it
- Observed with OpenRouter in v0.5.40

**Workaround:** bypass 9Router — point Hermes auxiliary.vision directly at upstream API.

## Models that CANNOT do vision (confirmed)

### ORCAROUTER — ALL models text-only
- `tencent/hy3` → "I cannot see the image" (image silently dropped)
- `deepseek/deepseek-v4-pro-free` → "Maaf, saya tidak bisa melihat gambar"
- All models: image_url content silently dropped by proxy

### Gemini CLI / Antigravity — DEAD
- Gemini CLI OAuth: 403 since June 18, 2026
- Antigravity CLI: 403 for consumer accounts

### Codex (ChatGPT account) — NOT a chat API
- Agent-only, all model names return 400

### OneRouter — vision needs credits
- `qwen/qwen3.8-max-preview:free` → text only (routed to alibaba/sg)
- All vision models need account balance ($5 min for :free tier)

### Bynara (router.bynara.id) — credits required
- 44 models but all need balance top-up

## Free vision options ranked (July 2026)

| Option | Vision | Free | Status |
|--------|--------|------|--------|
| OpenRouter `nemotron-nano-12b-v2-vl:free` | ✅ | ✅ | **ACTIVE — in use** |
| Google AI Studio API key | ✅ | 15 RPM | Available, not set up |
| DeepSeek API (direct) | ✅ | ~10M tokens trial | Available |
| ORCAROUTER | ❌ | Free calls | Text-only |
| OneRouter vision | ✅ | Needs $5 | Credits exhausted |

## Text-only models (confirmed working via 9Router)

| Provider | Model | Status |
|----------|-------|--------|
| OneRouter | `onerouter/qwen/qwen3.8-max-preview:free` | ✅ Active |
| ORCAROUTER | `tencent/hy3` | ✅ (free, text-only) |
| ORCAROUTER | `deepseek/deepseek-v4-pro-free` | ✅ (79 calls/day) |
