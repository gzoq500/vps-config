---
name: 9router-patching-pitfalls
description: Pitfalls when patching 9Router's compiled Next.js chunks
triggers:
  - 9router patch
  - 9router config change
  - minified JS patching
---

# 9Router Patching Pitfalls

## NEVER patch compiled chunks directly
- 9Router uses Next.js compiled chunks in `.next-cli-build/server/chunks/`
- Files are minified — single missing/extra char = SyntaxError breaks ALL providers
- `npm install` does NOT always restore modified files — need `rm` + reinstall

## What was tried and failed:
1. Adding quirks rule in chunk/318.js — wrong provider name (used "claude" instead of "cc")
2. Removing `interleaved-thinking` from header in chunk/7011.js — didn't fix the issue
3. Injecting `delete a.thinking` in execution handler chunk/8895.js — broke `let` statement syntax

## If you MUST patch:
1. Always backup: `cp file.js file.js.bak`
2. Use python3 for precise string replacement, NEVER sed on minified JS
3. Verify syntax: `node -c file.js` before restarting
4. To fully restore: `rm <file>` then `npm install -g 9router@<version> --force`

## Better alternatives:
- Use 9Router's web UI for model/provider config
- Use different provider (e.g., blackbox for claude-fable-5)
- Submit PR to 9Router repo for config-level overrides

## Adding providers via Web UI (SAFER than DB manipulation):
1. Login: `http://localhost:20128/login` (password: ${VPS_PASS})
2. Navigate: Providers → "Add OpenAI Compatible"
3. Fill form:
   - Name: friendly label
   - Prefix: used as model ID prefix (e.g., "onerouter")
   - API Type: Chat Completions (default)
   - Base URL: `https://llm.onerouter.pro/v1`
   - API Key: your key
4. **CRITICAL**: Tombol "Create" hanya aktif setelah form terisi lengkap DAN tervalidasi
5. Jika "Create" tidak aktif: pastikan semua field terisi, coba klik "Check" dulu
6. **NOTE**: SQLite manipulation DOES work for API routing (proven: OneRouter provider added via SQLite routes correctly). However, SQLite-added providers may not appear in the Web UI dashboard. For full UI + API functionality, prefer Web UI. For API-only (headless/automation), SQLite is fine — see `9router` skill `references/add-provider-via-sqlite.md` for the correct recipe (must create providerNodes row + link UUID).

## SSE Stream / Dashboard Live Update Patching (v0.5.40)
> Full patch scripts & module mappings: `references/sse-live-update-patch.md`

### Architecture understanding:
- Dashboard reads from SSE endpoint `/api/usage/stream`
- SSE calls `BY()` (getStats) for initial data, then listens to EventEmitter `M` for "update"/"pending" events
- Keepalive was `: ping` every 25s (comment only, no data)
- Event emitter only fires on request `DONE` — streaming requests that end as `ResponseAborted` (Hermes disconnects after getting response) do NOT trigger events
- `recentRequests` comes from in-memory ring buffer `J.items`, only populated on `DONE`
- `usageDaily` and `requestDetails` tables DO get updated (DB logging works), but dashboard "Recent Requests" reads from stale memory ring

### Patches applied (file: `server/app/api/usage/stream/route.js`):
1. **BY() timeout**: Wrap `await (0,v.BY)()` with `Promise.race` + 5s timeout, fallback to empty stats object
2. **rg() timeout**: Wrap `await (0,v.rg)()` with `Promise.race` + 3s timeout, fallback to empty arrays
3. **Keepalive → stats push**: Replace `: ping` every 25s with actual stats data every 5s using `BY()` + `rg()`

### Patch in chunk 4884.js (ring buffer refresh):
- Original: `if(!J.initialized){J.initialized=!0;try{J.items=...`
- Patched: `if(!0){try{J.items=...` — forces ring buffer to refresh from DB every time `Q()` is called
- This makes `recentRequests` in SSE data reflect actual DB state

### Known limitation (unfixable without deep routing patch):
- "Recent Requests" in dashboard still only shows requests that completed with `DONE` status
- Streaming requests aborted by client (Hermes) are logged to `requestDetails` DB table but NOT to the memory ring
- The `usageDaily` aggregate stats DO update correctly
- Workaround: "Details" tab and "Last Used" column show accurate data; "Recent Requests" list is eventually consistent

### CRITICAL: Dynamic import paths DO NOT WORK in patched chunks
- Attempted `await import("../../../chunks/4884.js")` inside SSE route → crashes silently
- Only use functions already available via the module's `require` bindings (e.g., `v.BY`, `v.rg`)

## Provider Prefix Collision Pitfall

- Prefix "openrouter" COLLIDES with 9Router's built-in OpenRouter Free Tier provider
- When routing `openrouter/model-name`, 9Router resolves to the built-in (empty) provider, NOT your custom node
- **Fix**: Use a different prefix (e.g., "or", "orouter", "openr") for custom OpenRouter nodes
- Same likely applies to other built-in provider names (gemini, deepseek, etc.)

## Adding Providers — Correct Method

### Method 1: Web UI (RECOMMENDED — syncs routing engine)
1. Login → Providers → click provider node → "Add API Key"
2. Fill: Name, API Key, Default Model, Priority
3. Click "Check" → must show "Valid"
4. Click "Save"
5. **No restart needed** — routing engine picks up immediately

### Method 2: Web UI "Add OpenAI Compatible" (for new provider nodes)
1. Providers → "Add OpenAI Compatible"
2. Fill: Name, Prefix, API Type, Base URL, API Key
3. Click "Create"
4. Then go into the new node → "Add API Key" (Method 1 above)
5. **Without step 4, routing will NOT work** — node exists but no credentials loaded

### Method 3: SQLite direct (ONLY for emergency/automation)
- Creates DB entries but routing engine may not load them until restart
- Even after restart, may not work if internal credential cache isn't synced
- Always prefer Method 1 or 2

## WAL Checkpoint Fix (for stuck logging)

If `requestDetails` stops getting new entries despite 9Router processing requests:
```bash
systemctl stop 9router
sqlite3 /root/.9router/db/data.sqlite "PRAGMA wal_checkpoint(TRUNCATE);"
systemctl start 9router
```
This flushes the WAL file and resets the write-ahead log state.

## Web UI login:
- URL: `http://localhost:20128/login`
- Password: ${VPS_PASS} (Golem's password)
- Setelah login, cookie session akan maintain auth

## References
- `references/sse-live-update-patch.md` — exact patch code for SSE + chunk 4884
- `references/sse-module-map.md` — module function mappings
- `references/patching-lessons-july-2026.md` — what worked, what broke, cascade failure patterns, backup/restore strategies

## Token Tracking via stream:false (WORKAROUND for v0.5.40)

Non-streaming requests (`"stream": false`) correctly capture real token counts in `usageHistory`. Streaming requests store `{prompt_tokens: 0, completion_tokens: 0}` because `saveRequestUsage()` only fires on `DONE` — aborted streams never trigger it.

**Impact:** With streaming, "Recent Requests" shows stale entries and tokens are 0. With `stream:false`, all metrics are accurate and live.

**Trade-off:** `stream:false` is slower (wait for full response) but logs correctly.

## SSE Keepalive Async Patch — WORKS with IIFE + "today" param

The keepalive CAN be patched to send real stats. Two critical requirements:

1. **Use IIFE** `(async()=>{...})()` inside `setInterval` — plain async arrow silently fails
2. **Use `BY("today")`** NOT `BY()` — default `"all"` queries entire `usageHistory` table (6000+ rows) and hangs

### Working replacement for `: ping`:
```javascript
(async()=>{try{let s=await(0,v.BY)("today");if(s)c.enqueue(a.encode(`data: ${JSON.stringify(s)}\n\n`));else c.enqueue(a.encode(": ping\n\n"))}catch(e){c.enqueue(a.encode(": ping\n\n"))}})()
```

Interval: 10s (not 25s). Sends full stats including `recentRequests` from DB.

### What DOES NOT work:
- Async arrow function directly in setInterval: `setInterval(async () => {...}, 10000)` → 0 messages
- `BY()` without param → hangs on large usageHistory tables
- Patching chunk 4884 ring buffer with dynamic imports → crashes silently

## Fresh Reinstall Workflow

```bash
npm uninstall -g 9router && npm install -g 9router
```
Database preserved. Restore providers via Python sqlite3 (NOT SQL dump). See `9router` skill `references/fresh-reinstall-and-provider-restore.md`.

## Chunk 4884 Filter Patch (minimally safe)

Only change `return!1` to `return!0` in the 0-token filter — 2 occurrences:
```
promptTokens&&0===a.completionTokens)return!1  →  return!0
```
This makes 0-token entries visible in Recent Requests. Does NOT break other functionality.
