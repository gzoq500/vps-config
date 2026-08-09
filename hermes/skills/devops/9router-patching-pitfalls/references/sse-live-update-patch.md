# 9Router SSE Live Update Patch (v0.5.40)

## File: `server/app/api/usage/stream/route.js`

### Patch 1: Keepalive → stats push (WORKING VERSION)
Replace the `: ping` content inside the keepalive setInterval:
```python
old = 'c.enqueue(a.encode(": ping\\n\\n"))'
new = '(async()=>{try{let s=await(0,v.BY)("today");if(s){c.enqueue(a.encode(`data: ${JSON.stringify(s)}\\n\\n`))}else c.enqueue(a.encode(": ping\\n\\n"))}catch(e){c.enqueue(a.encode(": ping\\n\\n"))}})()'
```

**CRITICAL**: Do NOT replace the entire setInterval handler — only replace the `: ping` content. Keep surrounding `try/catch` and `if(b.closed)` structure intact.

### Anti-patterns that FAILED:
- Replacing entire `setInterval(()=>{...},25e3)` block → SyntaxError or silent hang
- Using `async()=>` as setInterval callback → arrow function issues with `this`
- Dynamic imports inside patched code → `await import("../../../chunks/4884.js")` crashes silently
- Complex multi-line replacements → easy to break minified JS

## File: `server/chunks/4884.js`

### Patch 2: Zero-token filter (WORKING VERSION)
Allow entries with 0 tokens to show in Recent Requests:
```python
old = 'promptTokens&&0===a.completionTokens)return!1'
new = 'promptTokens&&0===a.completionTokens)return!0'
# Found in TWO places — replace both
```

### Patch 3: Ring buffer always refresh from DB
```python
old = 'if(!J.initialized){J.initialized=!0;try{J.items='
new = 'if(!0){try{J.items='
```

## SQLite trigger issue (`auto_usage_log`)
- Trigger defaults to 200/200 tokens when json_extract returns 0
- Creates fake data in usageHistory
- After reinstall, trigger is recreated from schema migration — may need to be dropped and recreated without defaults
- Dashboard reads from `tokens` JSON column (shows 0), not `promptTokens` column (shows 200)

## usageDaily regeneration after cleanup
```python
# Group usageHistory by date, sum tokens, insert into usageDaily
import sqlite3, json
from collections import defaultdict
from datetime import datetime

rows = conn.execute("SELECT timestamp, provider, model, promptTokens, completionTokens, cost FROM usageHistory").fetchall()
days = defaultdict(lambda: {"requests":0,"promptTokens":0,"completionTokens":0,"cost":0,"byProvider":{},"byModel":{}})
for row in rows:
    ts, provider, model, pt, ct, cost = row
    d = datetime.fromisoformat(ts.replace("Z","+00:00"))
    key = f"{d.year}-{d.month:02d}-{d.day:02d}"
    days[key]["requests"] += 1
    days[key]["promptTokens"] += pt or 0
    days[key]["completionTokens"] += ct or 0
    # ... byModel aggregation
for k, v in days.items():
    conn.execute("INSERT OR REPLACE INTO usageDaily(dateKey, data) VALUES(?,?)", (k, json.dumps(v)))
```

## Reinstall as ultimate reset
```bash
npm uninstall -g 9router && npm install -g 9router
# Database KEPT — providers, connections, API keys preserved
# Compiled files RESTORED to clean state
# Must: regenerate usageDaily, check trigger, re-apply minimal patches
```

## Key module mappings (chunk 4884.js, module 9248):
- `BY` → function `W` → getStats (reads usageDaily + usageHistory)
- `BY("today")` → only queries today's data (faster, less hang risk)
- `BY("all")` → queries ALL data (heavy, can hang with 6000+ rows)
- `rg` → function `T` → getPending (returns activeRequests + recentRequests from ring buffer)
- `_V` → `M` → global EventEmitter (`global._statsEmitter`)
- `N(event, delay)` → debounced emit scheduler
- `J` → `global._recentRing` → in-memory ring buffer for recent requests
- `Q()` → initializes/refreshes ring from DB
- `U(entry)` → saveRequestUsage (saves to usageHistory + usageDaily + updates ring)

## Provider prefix collision
- Prefix "openrouter" COLLIDES with built-in OpenRouter Free Tier
- Use different prefix (e.g., "or") for custom OpenRouter nodes

## Backup locations
- `/root/9router-backup-20260728-001641/` — original files before any patches
- `/root/9router-backup-20260728-125543/` — files after first round of patches
- `/root/9router-full-backup-20260728-093459/` — full database backup

## Web UI login
- URL: `http://localhost:20128/login`
- Password: `${VPS_PASS}`
