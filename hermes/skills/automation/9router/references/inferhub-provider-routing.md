# Inferhub via 9Router — provider routing

## Symptom
- `GET /v1/models` + API key → **200**, many models listed
- `POST /v1/chat/completions` with `model: free/grok/grok-4.5` → **404**  
  `No active credentials for provider: free`
- Same Inferhub key against `https://api.inferhub.dev/v1` works

## Root cause
9Router splits the model id and uses the **first segment** as the provider key.  
A custom openai-compatible node with prefix `free/grok` does **not** match requests that begin with `free/`.

## Fix (DB or dashboard)
1. Set custom provider **prefix to one segment**, e.g. `ih`
2. Keep `baseUrl=https://api.inferhub.dev/v1` and the Inferhub API key on the connection
3. Call models as:
   - `ih/free/grok/grok-4.5`  (text)
   - `ih/mimo-v2.5` / `ih/mimo-v2.5-pro` (vision candidates)
4. Restart 9router after DB edits: `systemctl restart 9router`

## Inspect DB
```bash
sqlite3 ~/.9router/db/data.sqlite \
  "SELECT name,data FROM providerNodes; SELECT name,isActive,data FROM providerConnections; SELECT key,name FROM apiKeys;"
```

## Verify ladder
1. Direct Inferhub chat with raw model id → proves key/upstream
2. 9Router models with Bearer key → proves gateway auth
3. 9Router chat with `ih/<upstream-id>` → proves routing
4. Only then wire Hermes/Cursor to `http://HOST:20128/v1`

## Vision note (updated 2026-07-22)
- InferHub marketplace shows `free/grok/grok-4.5` as text+image.
- For **reliable vision through 9Router**, use **xiaomi-mimo**:
  - ✅ `xiaomi-mimo/mimo-v2.5` / `mimo/mimo-v2.5` — content + `image_tokens`
  - ❌ `mimo-v2.5-pro` — no image endpoints
- `ih/mimo-v2.5` may return HTTP 200 with empty content; prefer `xiaomi-mimo/...` for Hermes vision.
- Always re-prove direct upstream if router path is empty/404.

## Image generation note
Do not use `/v1/images/generations` for free/grok. Use `/v1/responses` with full provider id + `tools:[{type:"image_generation"}]`. Direct Inferhub works but skips 9Router Usage.

See also:
- `references/vision-and-model-ids.md`
- `references/hermes-session-override-and-image-gen.md`
