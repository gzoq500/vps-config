# Free AI API Providers Catalog (August 2026)

Last updated: 2026-08-05

## Verified Working Providers

### Gnrt (api.gnrt.dev)
- **Base URL:** `https://api.gnrt.dev/v1`
- **Models:** 15 Qoder models (all Qwen-based, despite labels)
- **Balance:** Rp 8.500
- **Free models:** All 15 work
- **Key models:** qd/ultimate, qd/cantus, qd/performance, qd/efficient, qd/qmodel_38max, qd/kmodel_latest, qd/gm51model
- **Reality:** qd/ultimate labeled "Claude Opus 4.7" but self-reports as Qwen3.5. ALL models are Qwen.
- **Context:** 70K+ tokens verified on qd/qmodel_38max
- **Safety:** Very permissive — explains most hacking concepts, writes port scanners, SYN flood code
- **Notes:** Stable, fast, no timeouts. Best free option for general use.

### b.ai (api.b.ai)
- **Base URL:** `https://api.b.ai/v1`
- **Models:** 38 total
- **Free models (API):** qwen3.6-27b, kimi-k2.5, minimax-m2.7
- **Premium (deposit):** qwen3.8-max, claude-opus-5, gpt-5.6, gemini-3.6, deepseek-v4, etc
- **Reality:** qwen3.6-27b = Qwen3.6-27B-FP8 (Alibaba). kimi-k2.5 = real Kimi K2.5 (reasoning, 299 reasoning tokens). minimax-m2.7 = real MiniMax-M2.7 with `<think>` tags.
- **Notes:** Chat app (BAI) gives 300K free credits for ALL models. API key needs deposit for premium. qwen3.8-max works via app but not API.

### TokenRouter (api.tokenrouter.com)
- **Base URL:** `https://api.tokenrouter.com/v1`
- **Models:** 120 total
- **Free model:** moonshotai/kimi-k3-free only
- **Reality:** Real Kimi K3 with reasoning_content (323 reasoning tokens). Confirmed Moonshot AI.
- **Rate limit:** Very strict — 2-3 requests then silence for minutes
- **Notes:** Best for testing Kimi K3 identity, not for production use.

### HCNSEC (api.hcnsec.cn)
- **Base URL:** `https://api.hcnsec.cn/v1`
- **Models:** 21
- **Free models:** DeepSeek-V4-Flash, step-3.5-flash, step-3.5-flash-2603, kat-coder-pro-v2.5, sensenova-6.7-flash-lite, Qwen3.5-397B-A17B, Qwen3.6-35B-A3B
- **Quirk:** Some models re-route to different upstream (DeepSeek-V4-Pro → nemotron-3-ultra, Qwen3.5 → xopqwen36v35b)
- **Notes:** `auto` model routes to step-3.5-flash. Some timeouts.

### Aerolink (cgapi.aerolink.lat)
- **Base URL:** `https://cgapi.aerolink.lat/v1`
- **Models:** gpt-5.6-luna, gpt-5.6-sol, gpt-5.6-terra
- **Wire API:** `responses` (OpenAI Responses API format, `resp_` prefix IDs)
- **Reality:** Likely o1/o3-mini rebrand. All self-report "ChatGPT" cutoff June 2024. reasoning_tokens present.
- **Safety:** Luna = least filtered (writes exploit code). Sol = most filtered (refuses everything). Terra = mid.
- **Context:** ~114K tokens (Luna claims)
- **Notes:** Real OpenAI reasoning models, just renamed. Stable.

### Deepgram (api.deepgram.com)
- **Type:** STT + TTS (NOT LLM)
- **STT:** 424 models, 7 architectures (base, nova, nova-2, nova-3, polaris, whisper), 184 languages
- **TTS:** 102 voices (aura-2 engine)
- **Use case:** Audio transcription, text-to-speech
- **Notes:** Real Deepgram, not an LLM. Excellent for audio workflows.

### Keelcode (api.keelcode.ai)
- **Base URL:** `https://api.keelcode.ai/v1/messages` (Anthropic format ONLY)
- **Models:** 9 total (5 working: deepseek-v4-flash/pro, kimi-k3, kimi-k2.7-code, kimi-k2.6)
- **Free tier:** $11 credits (GPT+Claude $1/day, Open Models $10/day)
- **Reality:** Coding agent platform (like Cursor). Anthropic Messages API only, stream:true required.
- **Quirk:** Token generated via Google OAuth E2E flow (cloakbrowser). Short-lived, needs regeneration.
- **Proxy needed:** OpenAI→Anthropic translator on port 3456 (`/root/keelcode_proxy.py`)
- **9Router integration:** ✅ WORKING via proxy (prefix `kx/`). Model mapping: `gpt-4o-mini`→`deepseek-v4-flash`. 4 tokens with auto-rotation. systemd: `keelcode-proxy.service`.
- **Rate limits:** kimi-k3: 10 req/day/token. deepseek: higher. 4 tokens = 4x limits. Resets 00:00 UTC.

### Google Antigravity (via 9Router)
- **Type:** Built-in9Router v0.5.50 provider (no proxy needed)
- **Auth:** Google OAuth (requires real browser, not automated)
- **Models (13):** ag/gemini-3.6-flash-high/medium/low, ag/gemini-3.5-flash-*, ag/gemini-pro-agent, ag/claude-sonnet-4-6, ag/claude-opus-4-6-thinking, ag/gpt-oss-120b-medium, ag/gemini-3-flash
- **Status:** Token valid but Google returns `VALIDATION_REQUIRED` — account needs verification at myaccount.google.com
- **OAuth callback:** Goes to `localhost:20128/callback` — requires SSH tunnel from remote devices
- **Pitfall:** Google blocks automated browsers (Browserbase/Playwright) for OAuth. Must use real browser via SSH tunnel.
- **Pitfall:** Model locks accumulate after 403 errors. Clear via DB: delete `modelLock_*` entries, restart9router.

## Expired / Degraded Providers

### Xkiro (api.xkiro.com)
- **Status:** Expired / models became premium
- **Was:** Free mimo-v2.5-pro:free, mimo-v2.5:free
- **Now:** All models require paid plan

### RoutLLM (routllm.pro)
- **Status:** Upstream unstable (Gemini 502 errors)
- **Credits:** $33.62 available
- **Free plan:** Covers Gemini models only, but upstream is down
- **Notes:** Good for when Gemini recovers

### OneRouter (llm.onerouter.pro)
- **Status:** Credits exhausted ($0)
- **Free models:** 3 work (inclusionai/ling-3.0-flash:free, poolside/laguna-s-2.1:free, mindai/macaron-v1-venti:free)
- **Quirk:** Most `:free` models require $5+ balance anyway
- **Notes:** infron.ai backend

### Qoder (openapi.qoder.sh)
- **Status:** IDE-only, no REST API for chat completions
- **Credits:** 300 trial credits + 800 Qwen3.8-Max calls
- **Notes:** Use via Qoder Desktop/CLI, not via API

### SeekAI (seekai.cc)
- **Status:** Down — all models timeout/500
- **Models:** 19 registered (all returning upstream errors)
- **Notes:** Wait for recovery

## Model Identity Findings

### Confirmed Real Models
| Claimed Name | Real Identity | Evidence |
|---|---|---|
| qwen3.6-27b (b.ai) | Qwen3.6-27B-FP8 (Alibaba) | Self-report, model field |
| kimi-k2.5 (b.ai) | Kimi K2.5 (Moonshot AI) | Self-report, reasoning_content |
| minimax-m2.7 (b.ai) | MiniMax-M2.7 | `<think>` tags, name field |
| kimi-k3-free (TokenRouter) | Kimi K3 (Moonshot AI) | Self-report, reasoning_content |
| DeepSeek-V4-Flash (HCNSEC) | deepseek-ai/deepseek-v4-flash | Self-report |

### Confirmed Rebrands
| Claimed Name | Real Identity | Evidence |
|---|---|---|
| qd/ultimate (Gnrt) | Qwen3.5 | All models self-report Qwen3.5 |
| gpt-5.6-luna (Aerolink) | o1-mini (OpenAI) | resp_ IDs, reasoning_tokens, "ChatGPT" self-ID |
| gpt-5.6-sol (Aerolink) | o3-mini (OpenAI) | resp_ IDs, spreadsheet "AA" trick, most filtered |
| gpt-5.6-terra (Aerolink) | o1-mini variant | resp_ IDs, deterministic output |
| kimi-k3 (Keelcode) | Likely Claude 3.5/4 | Leaked "Claude Anthropic" in identity test, system prompt forces Kimi identity, cutoff "Claude 3 Aug 2023" |
| gpt-5.6-sol (Keelcode) | OpenAI o3 | Direct leak "OpenAI o3" when asked real ID |
| gpt-5.6-luna (Keelcode) | o1-mini | Cutoff June 2024, least filtered |
| gpt-5.6-terra (Keelcode) | o1-mini variant | Cutoff June 2024, deterministic |
| DeepSeek-V4-Pro (HCNSEC) | nemotron-3-ultra | Different model in response |

## Operational Notes

- **9Router is life support** — NEVER systemctl stop 9router. Always update with `npm i -g 9router@latest` first, then restart.
- **systemd for 9Router** — Restart=always, RestartSec=5, ExecStart without flags
- **requireApiKey** — Set via DB requires restart. Toggle in dashboard stays ON. Use `Authorization: Bearer <key>` header for all requests.
- **Keelcode proxy** — systemd: `keelcode-proxy.service`, port 3456, auto-restart. Token rotation across 4 accounts.
- **9Router SSRF protection** — Blocks 127.0.0.1/localhost/private IPs. Proxy MUST listen on 0.0.0.0 + use public IP in baseUrl.
- **9Router dashboard "Create" button** — Silently fails if default model shows "Invalid". Use browser console API instead: `fetch('/api/provider-nodes', {method:'POST', ...})`
- **Antigravity OAuth** — Callback goes to localhost:20128. From mobile: use SSH tunnel. Google blocks automated browsers.
