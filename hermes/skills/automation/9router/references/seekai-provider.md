# SeekAI Provider (`https://seekai.cc/v1`)

Free API with no wallet/plan required. Key format `sk-*`. OpenAI-compatible.

## Verified Working Models (Aug 2026)

| Model | Provider | Status |
|---|---|---|
| `gpt-5-5` | OpenAI | ✅ |
| `gpt-5-4` | OpenAI | ✅ |
| `gpt-5.6` | OpenAI | ✅ |
| `gpt-5-6-luna` | OpenAI | ✅ |
| `claude-opus-5` | Anthropic | ✅ |
| `claude-opus-4-7` | Anthropic | ✅ |
| `gemini-3-flash` | Google | ✅ |
| `grok-4-5` | xAI | ✅ |
| `DeepSeek-V4-Flash-0731` | DeepSeek | ✅ |

## Non-Working Models (timeout / no channel / error)

| Model | Error |
|---|---|
| `claude-sonnet-5` | timeout |
| `claude-opus-4-8` | timeout |
| `claude-fable-5` | timeout |
| `deepseek-v4-pro` | timeout |
| `gemini-3-1-pro` | timeout |
| `gemini-3-pro` | timeout |
| `gpt-5-6-terra` | timeout |
| `gpt-5-6-sol` | "No available channel" |
| `glm-5-2` | error |

## 9Router Integration

Prefix: `seekai`
Base URL: `https://seekai.cc/v1`
Models called as: `seekai/gpt-5-5`, `seekai/claude-opus-5`, etc.

## Notes

- Stability varies — some models may become unavailable intermittently
- Re-test before relying on specific models for production use
- No vision capability confirmed yet — test with image_url content type
