# SSE Live Update Patch Scripts

## Module Map (v0.5.40)

### SSE Route: `server/app/api/usage/stream/route.js`
- Module `v` = import from `47370` → re-exports from `9248`
- `v.BY` = `getUsageStats()` (function `W` in chunk 4884) — full stats from DB
- `v.rg` = `getActiveRequests()` (function `T` in chunk 4884) — pending + ring buffer
- `v._V` = `statsEmitter` (EventEmitter in chunk 4884)

### Chunk 4884.js — Key Functions
- `U(a)` = `saveRequestUsage(entry)` — writes to usageHistory + usageDaily + ring buffer
- `T()` = `getActiveRequests()` — returns {activeRequests, recentRequests, errorProvider}
- `W(a)` = `getUsageStats(period)` — full stats aggregation
- `Q()` = `ensureRingInitialized()` — loads ring buffer from DB once
- `N(event, delay)` = `scheduleStatsEvent` — debounced emit to statsEmitter
- `J` = `global._recentRing` — in-memory ring buffer {items: [], initialized: false}
- `M` = `global._statsEmitter` — EventEmitter instance

### Chunk 318.js — Streaming Response Handler
- TransformStream instances process SSE chunks from upstream
- `l.tV` = parse SSE line (returns {data, done} or null)
- `i.v` = transform chunk for OpenAI format
- `l.v8` = encode chunk as SSE string
- Streaming responses with `stream_options: {include_usage: true}` should include usage in final chunk

### Chat Route: `server/app/api/v1/chat/completions/route.js`
- Imports `handleChat` from `@/sse/handlers/chat.js`
- Which calls `handleChatCore` from `open-sse/handlers/chatCore.js`
- Core handler manages auth, format detection, provider selection, streaming proxy

## Patch: Keepalive → Stats (route.js)

Replace single `: ping` occurrence:
```
OLD: c.enqueue(a.encode(": ping\n\n"))
NEW: (async()=>{try{let s=await(0,v.BY)("today");if(s)c.enqueue(a.encode(`data: ${JSON.stringify(s)}\n\n`));else c.enqueue(a.encode(": ping\n\n"))}catch(e){c.enqueue(a.encode(": ping\n\n"))}})()
```

**CONFIRMED WORKING:** This async IIFE in setInterval works correctly — sends stats data every 10s. The key is using `(async()=>{...})()` IIFE pattern, NOT `async () => {}` as the setInterval callback (which sends 0 messages).

## Patch: 0-token Filter (chunk 4884.js)

Replace in 2 occurrences:
```
OLD: promptTokens&&0===a.completionTokens)return!1
NEW: promptTokens&&0===a.completionTokens)return!0
```

This is the ONLY safe patch — minimally changes display behavior without affecting data flow.

## Safe Restore

```bash
npm uninstall -g 9router && npm install -g 9router
```
Database preserved. All providers/keys intact. Compiled JS restored to clean state.
