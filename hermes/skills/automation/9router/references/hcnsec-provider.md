# HCNSEC Provider

**Base URL:** `https://api.hcnsec.cn/v1`
**API Key format:** `sk-4U3*`
**Prefix for9Router:** `hcnsec`

## Models (21 listed, ~8 working)

### ✅ Working (verified)

| Requested Model | Actual Model in Response | Notes |
|---|---|---|
| `DeepSeek-V4-Flash` | `deepseek-ai/deepseek-v4-flash` | ✅ Correct identity |
| `DeepSeek-V4-Pro` | `nvidia/nemotron-3-ultra-550b-a55b` | ⚠️ WRONG — routes to Nemotron! |
| `Qwen3.5-397B-A17B` | `xopqwen36v35b` | ⚠️ WRONG — not Qwen! |
| `Qwen3.6-35B-A3B` | `xopqwen36v35b` | ⚠️ WRONG — same as above |
| `kat-coder-pro-v2.5` | `kat-coder-pro-v2.5` | ✅ Correct |
| `sensenova-6.7-flash-lite` | `sensenova-6.7-flash-lite` | ✅ Correct |
| `step-3.5-flash` | `step-3.5-flash` | ✅ Correct |
| `step-3.5-flash-2603` | `step-3.5-flash-2603` | ✅ Correct |

### ❌ Not Working

| Model | Error |
|---|---|
| `Kimi-K2.6` | timeout |
| `MiniMax-M3` | timeout |
| `glm-5.1` | timeout |
| `glm-5.2` | timeout |
| `step-3.7-flash` | timeout |
| `sensenova-u1-fast` | "model is not found" |

## Key Findings

1. **CRITICAL: Model routing mismatch** — some models route to completely different providers (DeepSeek-V4-Pro → Nemotron, Qwen → xopqwen). Always check `model` field in response.
2. `auto` model routes to `stepfun-ai/step-3.7-flash` (which itself times out)
3. Audio/image models listed but untested: `step-image-edit-2`, `stepaudio-2.5-*`
4. All `owned_by: "openai"` in models list (even non-OpenAI models)
5. Stability varies — models that work may timeout on retry
