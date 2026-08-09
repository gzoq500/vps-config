---
name: keelcode-proxy
description: "Use when keelcode.ai proxy needs setup or token rotation."
triggers:
  - keelcode
  - openai anthropic proxy
  - keelcode proxy
  - kx model
---

# Keelcode Proxy

Translate OpenAI chat/completions format to Anthropic Messages format for keelcode.ai.

## Architecture

```
9Router (port 20128) → Proxy (port 3456, 0.0.0.0) → keelcode.ai
  model: kx/kimi-k3      OpenAI→Anthropic translator    Bearer auth
```

## Why Proxy Needed

9Router's OpenAI-compatible type sends `Authorization: Bearer` + OpenAI format. Anthropic-compatible sends `x-api-key`. keelcode expects Anthropic format + Bearer auth. Neither works. Proxy bridges the gap.

## Key Implementation Details

- **MUST listen on `0.0.0.0`** — 9Router SSRF blocks `127.0.0.1`/localhost
- **Must send `stream: true`** — keelcode only works with streaming, proxy converts SSE back to non-streaming
- **Model name mapping** — handle 9Router sending generic names that don't exist on keelcode
- **User-Agent** — keelcode may need specific UA to bypass Cloudflare

## Token Rotation (4 Accounts Active)

Each account gets ~10 requests/day per model. Stack accounts for 4x throughput (40 requests/day/model total).

Tokens file: `/root/.keelcode_tokens.json` (JSON array of Bearer tokens).
Rotate on 429 rate limit error — proxy automatically picks next token.

**Accounts (Aug 2026):** 4 registered via Google OAuth (tiranda, sopian, diana, fitri). 5 more failed (Google blocks automated login). Registration script: `/root/keelcode_register.py`.

**Token refresh:** Run `python3 /root/keelcode_register.py` to regenerate expired tokens. Saves to `/root/.keelcode_token` — copy to tokens JSON file.

**Systemd manages the proxy** — auto-restart on crash. Service: `keelcode-proxy.service`.

## Systemd Service

`/etc/systemd/system/keelcode-proxy.service`:
```ini
[Unit]
Description=Keelcode Proxy
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /root/keelcode_proxy.py 3456 0.0.0.0
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Register New Account

Script: `/root/keelcode_register.py` — Google OAuth via headless browser.
Accounts: `/root/accounts.txt` (email,password per line).
Run: `python3 keelcode_register.py --accounts accounts.txt --account-index N --headless`

## Working Models (Aug 2026)

kimi-k3, deepseek-v4-flash, deepseek-v4-pro, kimi-k2.6, kimi-k2.7-code — all 10/day/token.
gpt-5.6-luna/terra/sol, glm-5.2 — 503.

## Pitfalls
- **Proxy MUST be 0.0.0.0**: 9Router SSRF blocks localhost.
- **stream:true required**: keelcode returns empty without it.
- **Tokens expire**: Regenerate via register script on 401.
- **requireApiKey**: 9Router resets to true on restart. Use API keys.
