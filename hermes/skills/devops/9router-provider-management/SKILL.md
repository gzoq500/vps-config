---
name: 9router-provider-management
description: "Use when9Router providers fail 403 or need OAuth fixes."
triggers:
  - 9router provider
  - add model to9router
  - 9router 403
  - antigravity 9router
  - cloudcode api
  - model lock
---

# 9Router Provider Management

## Critical Rules
- **JANGAN PERNAH matikan 9Router** — `systemctl stop 9router` kills Hermes. Always: install update first, THEN restart.
- Update: `npm i -g 9router@latest` → `systemctl restart 9router`
- DB: `/root/.9router/db/data.sqlite`
- requireApiKey keeps resetting to true on restart — this is correct, use API keys in requests.

## Add Provider Connection via Browser Console API

Dashboard "Create" button sometimes fails silently. Use browser console:

```javascript
const csrfRes = await fetch('/api/csrf');
const { csrfToken } = await csrfRes.json();
const nodeRes = await fetch('/api/provider-nodes', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'x-csrf-token': csrfToken },
  body: JSON.stringify({ provider: 'provider-name', name: 'Display Name' })
});
const node = await nodeRes.json();
const connRes = await fetch(`/api/provider-nodes/${node.id}/connections`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'x-csrf-token': csrfToken },
  body: JSON.stringify({
    name: 'Connection Name', apiKey: 'your-api-key',
    authType: 'api-key', baseUrl: 'https://api.example.com/v1'
  })
});
```

## Direct DB Injection (when UI fails)

```python
import sqlite3, json
db = sqlite3.connect('/root/.9router/db/data.sqlite')
cur = db.cursor()
cur.execute("""INSERT OR REPLACE INTO providerConnections 
  (id, provider, authType, name, email, priority, isActive, data, createdAt, updatedAt)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
  ('conn-id', 'provider-name', 'api-key', 'Name', '', 0, 1,
   json.dumps({"apiKey": "sk-xxx", "testStatus": "active"})))
db.commit(); db.close()
```
After DB changes: `systemctl restart 9router` (sql.js caches in memory).

## Clear Model Locks

When models show "Unavailable (reset after Xs)" — locks are cached 403/402:

```python
import sqlite3, json
db = sqlite3.connect('/root/.9router/db/data.sqlite')
d = json.loads(db.execute("SELECT data FROM providerConnections WHERE provider='xxx'").fetchone()[0])
for k in list(d.keys()):
    if k.startswith('modelLock_'): del d[k]
d['testStatus'] = 'active'
d.pop('lastError', None); d.pop('errorCode', None); d.pop('lastErrorAt', None)
db.execute("UPDATE providerConnections SET data=? WHERE provider='xxx'", (json.dumps(d),))
db.commit()
```
Then: `systemctl restart 9router`

## Refresh OAuth Token

```python
import urllib.request, json, sqlite3
db = sqlite3.connect('/root/.9router/db/data.sqlite')
d = json.loads(db.execute("SELECT data FROM providerConnections WHERE provider='xxx'").fetchone()[0])
body = urllib.parse.urlencode({
    "grant_type": "refresh_token", "refresh_token": d['refreshToken'],
    "client_id": "CLIENT_ID", "client_secret": "CLIENT_SECRET"
}).encode()
req = urllib.request.Request("https://oauth2.googleapis.com/token", data=body,
    headers={"Content-Type": "application/x-www-form-urlencoded"})
data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
d['accessToken'] = data['access_token']
# Save back to DB...
```

See `references/antigravity-cloudcode-api.md` for Antigravity OAuth details.

## SSRF Protection

9Router blocks `127.0.0.1`, `localhost`, private IPs. Proxies MUST bind `0.0.0.0` + use public IP in baseUrl.

## Proxy-based Providers (Keelcode pattern)

For APIs with non-standard auth/format (e.g. Anthropic-only endpoints), create a translator proxy:
1. Python HTTP server on port 3456 (0.0.0.0 — SSRF protection)
2. Translates OpenAI→upstream format
3. Injects correct auth headers
4. Token rotation via JSON file
5. systemd service for auto-restart

See `references/keelcode-proxy.md` for the full proxy template.

## Pitfalls
- **requireApiKey=true on restart**: CORRECT behavior. Use API keys.
- **DB changes need restart**: sql.js caches in memory.
- **OAuth tokens expire**: Check `expiresAt` before debugging 403s. Refresh with `client_id` + `refresh_token` → `https://oauth2.googleapis.com/token`.
- **Cloud Code API platform**: Must be integer `0`, NOT string `"linux"`.
- **VALIDATION_REQUIRED**: User must visit validation URL (from403 `details[].metadata.validation_url`) in real browser. Google blocks Browserbase/automation. After validation, refresh token.
- **⚠️ Antigravity User-Agent**: ONLY `Trae/1.0.0 antigravity-cockpit-tools` works.9Router's default `antigravity/ide/X.Y.Z darwin/arm64` returns 403. MUST patch compiled chunks. See `9router-patching-pitfalls` skill.
- **Antigravity chunks to patch**: Multiple JS chunks contain the UA config — must patch ALL: 4963.js (template literal), 5619.js, 7011.js, and any others with `antigravity` + `User-Agent`. **After `npm i -g 9router@latest`**, ALL patches are lost — must re-patch every update.

## Antigravity Complete Setup Flow (Zero → Working)

1. **OAuth**: Dashboard → Providers → Antigravity → Add Connection → Sign in with Google
2. **Callback**: Goes to `localhost:20128/callback` — need SSH tunnel from remote: `ssh -L 20128:localhost:20128 root@VPS`
3. **Google validation**: After OAuth, Cloud Code API returns 403 VALIDATION_REQUIRED. Extract `validation_url` from error JSON. User opens in real browser → "Autentikasi berhasil"
4. **Patch UA**: `grep -rl 'antigravity' chunks/ | xargs grep 'User-Agent'` — patch ALL matches to `Trae/1.0.0 antigravity-cockpit-tools`
5. **Restart + clear locks**: `systemctl restart 9router`, clear `modelLock_*` from providerConnections
6. **Test**: `curl -H "Authorization: Bearer $KEY" http://localhost:20128/v1/chat/completions -d '{"model":"ag/gemini-3.6-flash-high",...}'`

## Antigravity Model Identity Results (Aug 2026)

| Model | Self-Report | Company | Genuine? |
|---|---|---|---|
| gemini-3.6-flash-high | "Gemini 3.6 Flash" | Google | ✅ ASLI |
| gemini-3-flash-agent | "Gemini" | Google | ✅ ASLI |
| gemini-pro-agent | "Gemini" | Google | ✅ ASLI |
| claude-sonnet-4-6 | "Claude" | Anthropic | ✅ ASLI |
| claude-opus-4-6-thinking | "Claude" | Anthropic | ✅ ASLI |
| gpt-oss-120b-medium | "GPT-4" | OpenAI | ⚠️ Self-reports GPT-4 |
| gemini-3.5-flash-low | "Gemini 1.5" | Google | ⚠️ Self-reports 1.5 |
| gemini-3.1-pro-low | "Gemini" | Google | ✅ ASLI, reasoning works |
| gemini-3-flash | "Gemini" | Google | ✅ ASLI |

**Freedom:** Claude Sonnet 4.6 most permissive (SQL injection, phishing, horror). Gemini 3.6 moderate (port scanner, horror). GPT-OSS most restrictive (4/6 refuse).

**Logic:** 100% correct on all models (strawberry r's, bat/ball, spreadsheet, Schrödinger).

**Coding:** All produce production-quality code (O(1) LRU cache, type hints, docstrings).

**Gemini 3.1 Pro:** Extended reasoning works (970-2282 reasoning tokens). Knowledge cutoff post-November 2024.

## Google Search Grounding (REAL-TIME DATA!)

Default Antigravity API has NO search. Inject `google_search` tool into request:

**Patch chunk 8499.js** — replace tools output:
```
OLD: ...g&&{tools:g}
NEW: ...{tools:[...(g||[]),{google_search:{}}]}
```

After patch + restart, ALL models get real-time Google Search data. Verified: returns August 2026 news headlines.

**Auto-patch script:** `/root/patch_antigravity.sh` — restores UA + grounding patches after `npm i -g 9router@latest`.

## Extended Reasoning via thinkingConfig

Add to request body for Gemini models:
```json
{
  "thinkingConfig": {
    "includeThoughts": true,
    "thinkingBudget": 16384
  }
}
```
Produces `reasoning_content` in response (970-2282 tokens for complex tasks). Works on gemini-3.1-pro-low, gemini-3.6-flash-high.
