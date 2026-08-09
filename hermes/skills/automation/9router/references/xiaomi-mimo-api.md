# Xiaomi MiMo API — Official Endpoint & Model Capabilities

## Official API: `api.xiaomimimo.com/v1`

- **Base URL:** `https://api.xiaomimimo.com/v1`
- **Auth:** `Authorization: Bearer <API_KEY>` (from platform.xiaomimimo.com)
- **Format:** OpenAI-compatible (`/v1/chat/completions`)

## Models (July 2026)

| Model | Chat | Vision | Notes |
|-------|------|--------|-------|
| `mimo-v2.5-pro` | ✅ | ❌ | Returns "No endpoints found that support image input" for image_url |
| `mimo-v2.5` | ❌ | ❌ | Returns "Param Incorrect" for image_url content |

## Key Findings

1. **mimo-v2.5-pro does NOT support vision via official API** — despite docs claiming "multimodal", the API rejects image input with `No endpoints found that support image input`. Model docs are misleading.

2. **mimo-v2.5 returns "Param Incorrect"** — different error than pro, suggests model doesn't even parse image_url format.

3. **Chat works perfectly** — mimo-v2.5-pro returns correct content with reasoning_content (thinking tokens). Math, code, general chat all functional.

4. **Vision workaround** — Use XKiro (`api.xkiro.com/v1`) with `nvidia/nemotron-3-nano-omni` for vision. Or OpenRouter free `nvidia/nemotron-nano-12b-v2-vl:free`.

## XKiro mimo-v2.5:free Vision Trick

- Model CAN process images via XKiro (different from official API)
- Returns empty `content` if `max_tokens` ≤ 20 (reasoning tokens consume budget)
- Set `max_tokens: 100+` and use strict prompt ("One word only") to get vision output
- With `max_tokens: 20`: only `reasoning_content` populated, `content` is empty string
- With `max_tokens: 100`: correctly identifies image content (e.g., "Red" for red square)

## Comparison: Where to get MiMo vision

| Provider | Model | Vision | Cost |
|----------|-------|--------|------|
| xiaomimimo.com | mimo-v2.5-pro | ❌ | Paid |
| xiaomimimo.com | mimo-v2.5 | ❌ | Paid |
| XKiro | mimo-v2.5:free | ✅ (with 100+ tokens) | Free |
| XKiro | nvidia/nemotron-3-nano-omni | ✅ | Free |
| OpenRouter | nvidia/nemotron-nano-12b-v2-vl:free | ✅ | Free |
