# New Free Providers Discovered (August 2026)

## Gnrt.dev
- **Base URL:** `https://api.gnrt.dev/v1`
- **Key:** `sk-gnrt-*`
- **Models:** 15 (all self-identify as Qwen3.5 despite dashboard labels)
- **Best model:** `qd/qmodel_38max` (Qwen 3.8 Max) — 70K+ context, very permissive safety, 10/10 coding tasks
- **Labels are FAKE:** `qd/ultimate` labeled "Claude Opus 4.7" but is Qwen3.5
- **Balance:** Rp8.500

## b.ai
- **Base URL:** `https://api.b.ai/v1`
- **Key:** `sk-*`
- **Free models:** `qwen3.6-27b` (Alibaba Qwen3.6-27B-FP8), `kimi-k2.5` (Moonshot, reasoning), `minimax-m2.7` (MiniMax, thinking tags)
- **38 total models**, premium requires deposit
- **API vs Chat App:** qwen3.8-max works in chat app (free registration credits) but not API

## TokenRouter
- **Base URL:** `https://api.tokenrouter.com/v1`
- **Key:** `sk-*`
- **Free model:** `moonshotai/kimi-k3-free` only (real Kimi K3, reasoning model)
- **120 total models**, all others need credits ($0 balance)
- **Rate limited:** 2-3 requests then empty for minutes

## Keelcode.ai
- **Base URL:** `https://api.keelcode.ai/v1/messages` (Anthropic format)
- **Token:** generated via Google OAuth device flow (`keelcode_register.py`)
- **Free models:** deepseek-v4-flash, deepseek-v4-pro, kimi-k3, kimi-k2.7-code, kimi-k2.6, gpt-5.6-luna, gpt-5.6-sol, gpt-5.6-terra (7/9 work, glm-5.2+gpt-5.6-terra=503)
- **CRITICAL:** stream:true ONLY, cache_control required, needs proxy for OpenAI format
- **Daily credits:** $1 GPT+Claude, $10 Open Models
- **Rate limits:** kimi-k3=10/day/token, others more generous, per-model separate limits
- **Token rotation:** Register multiple Google accounts → collect tokens → proxy auto-rotates on 429
- **Registration:** `python3 keelcode_register.py --accounts accounts.txt --headless` (Google OAuth via headless Playwright, some accounts fail at google_login stage)
- **4 tokens = 4x daily limits** per model
- **Models are REBRANDED** — see references/keelcode-identity-investigation.md
- **9Router integration:** proxy translator at port 3456, systemd keelcode-proxy.service, prefix kx/

## HCNSEC
- **Base URL:** `https://api.hcnsec.cn/v1`
- **Key:** `sk-4U3*`
- **Free models:** DeepSeek-V4-Flash, step-3.5-flash, kat-coder-pro-v2.5, sensenova-6.7-flash-lite
- **WARNING:** Model routing mismatch — `DeepSeek-V4-Pro` actually serves `nvidia/nemotron-3-ultra`
- **8 working models** out of 21 listed

## Aerolink
- **Base URL:** `https://cgapi.aerolink.lat/v1` (NOT aerolink.lat — Cloudflare challenge)
- **Key:** `aero_live_*`
- **Models:** gpt-5.6-luna, gpt-5.6-sol, gpt-5.6-terra
- **All are o1/o3 rebranded** — reasoning_tokens, CoT hidden, "ChatGPT" self-identify, June 2024 cutoff
- **Luna = least filtered** (writes exploit code), Sol = most filtered, Terra = middle

## Deepgram
- **Base URL:** `https://api.deepgram.com/v1`
- **Key:** Token format (32-char hex)
- **NOT an LLM** — Speech-to-Text (424 models, 7 architectures) + Text-to-Speech (102 voices)
- **184 languages** supported
- **Models:** nova-3 (newest), nova-2, polaris (specialized), whisper, base
