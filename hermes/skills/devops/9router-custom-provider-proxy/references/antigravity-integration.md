# Google Antigravity Integration with 9Router

## Overview
Google Antigravity (antigravity.google) is Google's coding agent platform. 9Router v0.5.50 has **built-in** Antigravity support — intercepts traffic from `cloudcode-pa.googleapis.com` via MITM proxy.

## How It Works
```
Antigravity CLI → cloudcode-pa.googleapis.com
       ↓ (DNS redirect to localhost)
9Router MITM Proxy (port 20128)
       ↓
Routes to Google's Cloud Code API with OAuth token
```

## Setup Steps
1. Go to9Router dashboard → Providers → Antigravity
2. Click "Add" to add connection
3. Login with Google account (OAuth flow)
4. Token stored in `providerConnections` table (provider='antigravity')
5. Models auto-discovered (13+ models available)

## Model List (as of Aug 2026)
| Model ID | Name | Vision | Reasoning |
|---|---|---|---|
| ag/gemini-3.6-flash-high | Gemini 3.6 Flash (High) | ✅ | ✅ |
| ag/gemini-3.6-flash-medium | Gemini 3.6 Flash (Medium) | ✅ | ✅ |
| ag/gemini-3.6-flash-low | Gemini 3.6 Flash (Low) | ✅ | ✅ |
| ag/gemini-3.5-flash-high | Gemini 3.5 Flash (High) | ✅ | ✅ |
| ag/gemini-3-flash-agent | Gemini 3.5 Flash (High) | ✅ | ✅ |
| ag/gemini-3.5-flash-low | Gemini 3.5 Flash (Medium) | ✅ | ✅ |
| ag/gemini-3.5-flash-extra-low | Gemini 3.5 Flash (Low) | ✅ | ✅ |
| ag/gemini-pro-agent | Gemini 3.1 Pro (High) | ✅ | ❌ |
| ag/gemini-3.1-pro-low | Gemini 3.1 Pro (Low) | ✅ | ✅ |
| ag/claude-sonnet-4-6 | Claude Sonnet 4.6 (Thinking) | ✅ | ✅ |
| ag/claude-opus-4-6-thinking | Claude Opus 4.6 (Thinking) | ✅ | ✅ |
| ag/gpt-oss-120b-medium | GPT-OSS 120B (Medium) | ❌ | ✅ |
| ag/gemini-3-flash | Gemini 3 Flash | ✅ | ✅ |

## OAuth Token Structure
Connection data contains:
- `accessToken` — Google OAuth access token (ya29.*)
- `refreshToken` — For auto-refresh (1//058_*)
- `expiresAt` — Token expiry (ISO timestamp)
- `projectId` — Google Cloud project
- `scope` — cloud-platform, cclog, etc.
- `testStatus` — "active" when working
- `lastError` — Error message if failed
- `modelLock_<model>` — Timestamp when model was locked due to 403

## Token Refresh
1. Click "Test Connection One-by-One" in dashboard
2. 9Router auto-refreshes token via refreshToken
3. Status updates from "unavailable" to "active"

## Troubleshooting

### 403 "Verify your account to continue" (VALIDATION_REQUIRED)
Google account needs verification. User must:
1. Login to Google account in browser
2. Complete phone/CAPTCHA verification
3. Then Antigravity works automatically

### OAuth Callback = localhost (ERR_CONNECTION_REFUSED from mobile)
Antigravity OAuth callback goes to `localhost:20128/callback`. From mobile/remote:
```bash
ssh -L 20128:localhost:20128 root@209.127.114.234
# Then open http://localhost:20128/dashboard/providers/antigravity in browser
```
Google blocks automated browsers (Browserbase/Playwright) — must use real browser via SSH tunnel.

### Models show "Unavailable" after token refresh
Model locks persist in DB. Clear them:
```python
import sqlite3, json
db = sqlite3.connect('/root/.9router/db/data.sqlite')
cur = db.cursor()
cur.execute('SELECT data FROM providerConnections WHERE provider="antigravity"')
data = json.loads(cur.fetchone()[0])
for k in [k for k in data if k.startswith('modelLock_')]: del data[k]
data['lastError'] = None; data['errorCode'] = None
cur.execute('UPDATE providerConnections SET data=? WHERE provider="antigravity"', (json.dumps(data),))
db.commit()
```
Then: `systemctl restart 9router`

### Rate limits
Antigravity has per-model rate limits from Google. If hitting limits, wait or use different Google account.

### Dashboard "Test" Shows Green But API Returns 403
Dashboard "Test Connection" checks token format, not actual API call. A green "Passed: 1" doesn't guarantee models work. Check `testStatus` and `lastError` in DB for real status, or test directly:
```bash
curl -s http://localhost:20128/v1/chat/completions \
  -H "Authorization: Bearer <9router-key>" \
  -H "Content-Type: application/json" \
  -d '{"model":"ag/gemini-3.6-flash-high","messages":[{"role":"user","content":"Say OK"}],"max_tokens":50}'
```

## Risk Warning
9Router dashboard shows: "⚠️ Risk Notice: This provider uses a subscription/OAuth session not officially licensed for proxy/router use. Account may be restricted or banned. Use at your own risk."

## Antigravity CLI (installed on VPS)
```bash
curl -fsSL https://antigravity.google/cli/install.sh | bash
# Installs to /root/.local/bin/agy (v1.1.11)
# Needs TTY for interactive login — use PTY mode or script -qc
```
CLI needs interactive TTY for OAuth login. `agy --print` works non-interactively after auth.
The CLI is separate from9Router's built-in Antigravity provider — it's for running agents directly, not for9Router model routing.

## OAuth Flow Detail (Aug 2026)
1. Dashboard "Add Connection" → shows risk notice → "I Understand, Continue"
2. Opens Google OAuth in new tab → account chooser → consent page
3. After consent, redirects to `localhost:20128/callback?state=...&code=...`
4. **From mobile:** callback fails (localhost = phone, not VPS). Must copy URL and send to agent, or use SSH tunnel.
5. **From Browserbase:** Google blocks with "This browser or app may not be secure"
6. **Working method:** SSH tunnel from mobile → `ssh -L 20128:localhost:20128 root@VPS` → open localhost:20128 in browser

## Free Models via Antigravity
All Antigravity models are **FREE** with a Google account (no subscription needed for basic access). This is the cheapest way to get Gemini 3.6 Flash, Claude Sonnet 4.6, and GPT-OSS models.
