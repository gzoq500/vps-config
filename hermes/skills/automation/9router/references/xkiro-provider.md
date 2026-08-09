# XKiro Provider Integration

## API Details
- **Base URL:** `https://api.xkiro.com/v1`
- **Auth:** Bearer token (`sk-xt-*`)
- **Format:** OpenAI-compatible
- **Free models available:** ~49 total (July 2026)

## Free Models
| Model | Type | Vision |
|-------|------|--------|
| `xiaomi/mimo-v2.5-pro:free` | Chat | ❌ (returns empty on images) |
| `xiaomi/mimo-v2.5:free` | Chat | ❌ (returns empty on images) |
| `nvidia/nemotron-3-nano-omni` | Chat+Vision | ✅ (confirmed) |
| `nvidia/nemotron-3-super` | Chat | Unknown |
| `nvidia/nemotron-3-ultra` | Chat | Unknown |

## 9Router Setup
1. Web UI → Add OpenAI Compatible
2. Name: `XKiro`, Prefix: `xkiro`
3. Base URL: `https://api.xkiro.com/v1`
4. API Type: Chat Completions
5. Add API Key with model `xiaomi/mimo-v2.5-pro:free`
6. Call as: `xkiro/xiaomi/mimo-v2.5-pro:free`

## Vision via Hermes
Set auxiliary vision directly (bypass 9Router):
```bash
hermes config set auxiliary.vision.model nvidia/nemotron-3-nano-omni
hermes config set auxiliary.vision.base_url https://api.xkiro.com/v1
hermes config set auxiliary.vision.api_key sk-xt-YOUR_KEY
```

## Notes
- Works with `stream:false` for proper token logging
- `nvidia/nemotron-nano-12b-v2-vl` does NOT exist on XKiro (different from OpenRouter)
- Token counts are real (not 0) when using non-streaming
