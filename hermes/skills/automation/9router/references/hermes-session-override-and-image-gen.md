# Hermes session override + Inferhub image gen (session 2026-07-23)

## Symptom A — chat missing from 9Router Usage
Dashboard topology shows Inferhub / Xiaomi connected, but RECENT REQUESTS only shows some models (or none of the current chat).

### Cause
Hermes can hold a **per-session model_override** that ignores `config.yaml`.

Observed live values:
```json
{
  "model": "free/grok/grok-4.5",
  "provider": "custom:inferhub",
  "base_url": "https://api.inferhub.dev/v1"
}
```
That traffic never hits `HOST:20128`, so it never logs in 9Router Usage.

Gateway log signature:
```text
Rehydrated persisted /model override ... provider=custom:inferhub base_url=https://api.inferhub.dev/v1
API call ... provider=custom:inferhub model=free/grok/grok-4.5
```

### Where override lives
1. `~/.hermes/sessions/sessions.json` → `agent:main:telegram:dm:<chat_id>.model_override`
2. `~/.hermes/state.db` → `gateway_routing.entry_json` (same key)
3. `~/.hermes/state.db` → `sessions.model` + `sessions.model_config.gateway_runtime` + `billing_base_url`

### Safe fix (do not kill 9Router)
1. Patch override to local 9Router:
   - model: `mimo/mimo-v2.5-pro` (chat)
   - base_url: `http://127.0.0.1:20128/v1` (or public IP of THIS 9Router)
   - provider: `custom` (not `custom:inferhub`)
2. Ask user to send `/model mimo/mimo-v2.5-pro` or `/new` (gateway may keep old override in memory)
3. Verify with a test chat and `requestDetails` / Usage table

### Verify ladder
```bash
# 9Router healthy
systemctl is-active 9router
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $KEY" http://127.0.0.1:20128/v1/models

# chat through 9Router
curl -s -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"mimo/mimo-v2.5-pro","messages":[{"role":"user","content":"Reply exactly: OK"}],"max_tokens":40,"stream":false}' \
  http://127.0.0.1:20128/v1/chat/completions

# recent log
sqlite3 ~/.9router/db/data.sqlite \
  "SELECT timestamp,model,status,provider FROM requestDetails ORDER BY timestamp DESC LIMIT 10;"
```

If 9Router chat works but Hermes still fails → Hermes routing/override, not 9Router death.

## Symptom B — image gen empty / not logged
Working image gen uses **Responses API + tool**, not chat completions.

```json
POST /v1/responses
{
  "model": "openai-compatible-responses-<uuid>/free/grok/grok-4.5",
  "input": "<prompt>",
  "tools": [{"type": "image_generation"}]
}
```

| Path | Result |
|------|--------|
| 9Router `/v1/responses` + full provider id | ✅ image b64, logged in Usage |
| 9Router `/v1/images/generations` | ❌ provider does not support image generation |
| 9Router model `free/grok/grok-4.5` raw | ❌ provider `free` not found |
| Direct `api.inferhub.dev/v1/responses` | ✅ works, **no** 9Router Usage entry |

Dashboard model list may show doubled id `free/grok/free/grok/grok-4.5` when custom model id already includes the prefix. Prefer custom model id `grok-4.5` under prefix `free/grok`, or call full provider id.

## Topology vs Usage
- Topology nodes = configured/connected providers
- RECENT REQUESTS = actual traffic through this router only
- Direct Inferhub / other 9Router hosts (`178.x`, etc.) will not appear here

## User safety preference
If user says not to kill the parts that keep the agent alive:
- Do **not** restart 9Router casually
- Do **not** `hermes gateway restart` from inside the gateway tool loop
- Prefer file/DB/session patches + user `/model` or `/new`

## Related
- `references/inferhub-provider-routing.md` — prefix `ih` / first-segment routing
- `references/vision-and-model-ids.md` — vision model ids
