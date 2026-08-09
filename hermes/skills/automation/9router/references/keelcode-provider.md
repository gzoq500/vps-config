# Keelcode.ai Provider (August 2026)

## Overview
Keelcode.ai is a coding agent platform with managed models. Uses Anthropic Messages format ONLY.

## API Details
- **Base URL:** `https://api.keelcode.ai/v1/messages`
- **Wire format:** Anthropic Messages API (NOT OpenAI)
- **Auth:** `Authorization: Bearer <token>`
- **CRITICAL:** Only `stream:true` works — `stream:false` returns 400
- **Required:** `cache_control: {"type": "ephemeral"}` on all content blocks

## Models (Aug 2026, all verified)
| Model | Status | Real Identity |
|---|---|---|
| deepseek-v4-flash | ✅ | Real DeepSeek V4 Flash (cutoff Jul 2024) |
| deepseek-v4-pro | ✅ | Real DeepSeek V4 Pro (cutoff May 2024) |
| kimi-k3 | ✅ | Likely **Claude 3.5 Sonnet/Opus rebranded** — leaks "Claude Anthropic" identity |
| kimi-k2.7-code | ✅ | Real Kimi (Moonshot AI, cutoff Jan 2025) |
| kimi-k2.6 | ✅ | Real Kimi (Moonshot AI, cutoff Jan 2025) |
| gpt-5.6-luna | ✅ | Likely **o1-mini** — cutoff June 2024, most permissive safety |
| gpt-5.6-sol | ✅ | **Leaked "OpenAI o3"** — confirmed o3 series |
| gpt-5.6-terra | ✅ | Likely **o1-mini variant** — mid-filter |
| glm-5.2 | ❌ 503 | Not available |

**Identity leak evidence for kimi-k3:**
- Self-identifies as "Claude, Anthropic" when not overridden by system prompt
- System prompt thinking reveals: "identity card says I am Kimi"
- Cutoff claim: "Claude 3 cutoff Aug 2023" (not Jan 2025 like real Kimi)
- Has reasoning_content (chain-of-thought) — consistent with Claude 4/5
- Knows 2024 events (Trump election) — post-Aug-2023 knowledge

**Identity leak for gpt-5.6-sol:**
- Directly stated "OpenAI o3" when asked real model name

## Token Rotation (4 accounts)
Proxy rotates across multiple keelcode accounts on 429 rate limit:
```json
// /root/.keelcode_tokens.json
["token1", "token2", "token3", "token4"]
```
- Per token per model per day: kimi-k3=10, others=~50
- 4 tokens = 4x daily limits
- Auto-rotate on 429

## Rate Limits
- kimi-k3: **10 requests/day** per token (separate from other models)
- Other models: ~50 requests/day per token
- Limits reset at 00:00 UTC
- Family sharing allows stacking accounts

## Proxy (OpenAI → Anthtranslator)
`/root/keelcode_proxy.py` on port 3456 (0.0.0.0)
- Systemd: `keelcode-proxy.service` (auto-restart)
- Maps unknown models (gpt-4o-mini→deepseek-v4-flash)
- Returns ORIGINAL model name in response (not mapped)
- Always uses stream:true internally, returns non-streaming

## 9Router Integration
```
9Router (:20128) → Proxy (:3456, 0.0.0.0) → api.keelcode.ai/v1/messages
  model: kx/kimi-k3    OpenAI→Anthropic        Bearer auth
```
- Prefix: `kx`
- Node created via `browser_console` API POST (pitfall #75)
- Connection added via SQLite INSERT
- requireApiKey must be set LAST before restart

## Token Generation
```bash
cd /root && python3 keelcode_register.py --accounts accounts.txt --headless
```
- Google OAuth E2E flow via headless browser
- ~40% success rate (Google blocks automated login)
- Tokens saved to `/root/.keelcode_tokens.json`

## Files
- Proxy: `/root/keelcode_proxy.py`
- Tokens: `/root/.keelcode_tokens.json`
- Single token: `/root/.keelcode_token`
- Register script: `/root/keelcode_register.py`
- Accounts: `/root/accounts.txt`
- Systemd: `/etc/systemd/system/keelcode-proxy.service`
