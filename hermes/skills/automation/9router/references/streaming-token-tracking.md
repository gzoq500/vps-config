# Streaming Token Tracking & SSE Live Update

## The Core Problem (v0.5.40)

9Router's `saveRequestUsage()` (function `U` in chunk 4884) only fires when a request completes with status `DONE`. Streaming requests where the client disconnects (`ResponseAborted`) never trigger this function, resulting in `{prompt_tokens: 0, completion_tokens: 0}` being stored.

## What This Affects

| Component | Streaming (stream:true) | Non-streaming (stream:false) |
|-----------|------------------------|------------------------------|
| usageHistory tokens | 0/0 | Real counts |
| usageDaily aggregation | Only counts, no token data | Full token data |
| Dashboard "Total Input Tokens" | Inaccurate | Accurate |
| Dashboard "Recent Requests" | Only shows DONE entries | Shows all entries |
| requestDetails | Logged but tokens=0 | Logged with real tokens |

## Root Cause Chain

1. Client sends `stream:true` request
2. 9Router forwards to upstream, pipes streaming response
3. Client (Hermes) disconnects after receiving enough data
4. 9Router marks as `ResponseAborted`
5. `handleDisconnect` callback fires but does NOT call `saveRequestUsage`
6. Tokens stored as `{0, 0}` in requestDetails
7. Dashboard shows stale token counts

## Known Fixes

### Fix 1: Use stream:false (recommended for accuracy)
Trade-off: Slower responses but accurate logging.

### Fix 2: Remove 0-token filter (cosmetic fix)
In chunk 4884.js, change `return!1` to `return!0` in the filter:
```
promptTokens&&0===a.completionTokens)return!1
```
This shows 0-token entries in Recent Requests but doesn't fix the underlying 0/0 issue.

### Fix 3: Regenerate usageDaily from usageHistory
After switching to stream:false, usageDaily needs regeneration:
```python
import sqlite3, json
from collections import defaultdict
from datetime import datetime

DB = "/root/.9router/db/data.sqlite"
conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("DELETE FROM usageDaily")

rows = c.execute("SELECT timestamp, provider, model, promptTokens, completionTokens, cost FROM usageHistory").fetchall()
days = defaultdict(lambda: {"requests":0,"promptTokens":0,"completionTokens":0,"cachedTokens":0,"cost":0,"byProvider":{},"byModel":{},"byAccount":{},"byApiKey":{},"byEndpoint":{}})

for row in rows:
    ts, provider, model, pt, ct, cost = row
    if not ts: continue
    d = datetime.fromisoformat(ts.replace("Z","+00:00"))
    date_key = f"{d.year}-{d.month:02d}-{d.day:02d}"
    day = days[date_key]
    day["requests"] += 1
    day["promptTokens"] += pt or 0
    day["completionTokens"] += ct or 0
    day["cost"] += cost or 0

for date_key, data in days.items():
    c.execute("INSERT OR REPLACE INTO usageDaily(dateKey, data) VALUES(?,?)", (date_key, json.dumps(data)))

conn.commit()
conn.close()
```

## SSE Keepalive Patch Status

**Attempted (failed):** Replace `: ping` with `getUsageStats()` via async IIFE in `setInterval`.
**Result:** Silent failure — SSE sends 0 messages. Async IIFE doesn't work in Next.js SSE context.

**Working pattern (tested July 2026):**
Replace `c.enqueue(a.encode(": ping\\n\\n"))` in route.js with:
```javascript
(async()=>{try{let s=await(0,v.BY)("today");if(s){c.enqueue(a.encode(`data: ${JSON.stringify(s)}\\n\\n`))}else c.enqueue(a.encode(": ping\\n\\n"))}catch(e){c.enqueue(a.encode(": ping\\n\\n"))}})()
```
Key: use `"today"` param (not default `"all"`) — queries only today's data, avoids hang on large usageHistory.
Interval: change `25e3` to `10e3` for faster updates.
This sends full stats including recentRequests from DB every 10 seconds.
**However:** after 9Router reinstall, patch must be re-applied. The SSE route file is at:
`/usr/local/lib/node_modules/9router/app/.next-cli-build/server/app/api/usage/stream/route.js`

## usageDaily Regeneration (Improved Script)

usageDaily does NOT auto-regenerate after data cleanup. Always regenerate after bulk deletes.

```python
import sqlite3, json
from collections import defaultdict
from datetime import datetime

DB = "/root/.9router/db/data.sqlite"
conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("DELETE FROM usageDaily")

rows = c.execute("SELECT timestamp, provider, model, connectionId, "
    "promptTokens, completionTokens, cost, status, tokens FROM usageHistory").fetchall()

days = defaultdict(lambda: {"requests":0,"promptTokens":0,"completionTokens":0,
    "cachedTokens":0,"cost":0,"byProvider":{},"byModel":{},"byAccount":{},
    "byApiKey":{},"byEndpoint":{}})

for row in rows:
    ts, provider, model, conn_id, pt, ct, cost, status, tokens_json = row
    if not ts: continue
    d = datetime.fromisoformat(ts.replace("Z","+00:00"))
    date_key = f"{d.year}-{d.month:02d}-{d.day:02d}"
    day = days[date_key]
    day["requests"] += 1
    day["promptTokens"] += pt or 0
    day["completionTokens"] += ct or 0
    day["cost"] += cost or 0
    mk = f"{model}|{provider}" if provider else model
    if mk not in day["byModel"]:
        day["byModel"][mk] = {"requests":0,"promptTokens":0,"completionTokens":0,
            "cachedTokens":0,"cost":0,"rawModel":model,"provider":provider or ""}
    day["byModel"][mk]["requests"] += 1
    day["byModel"][mk]["promptTokens"] += pt or 0
    day["byModel"][mk]["completionTokens"] += ct or 0

for date_key, data in days.items():
    c.execute("INSERT OR REPLACE INTO usageDaily(dateKey, data) VALUES(?,?)",
              (date_key, json.dumps(data)))
conn.commit()
conn.close()
```

## auto_usage_log Trigger

The trigger on `requestDetails` only fires for models matching `%grok%`, `%mimo%`, or `%free%`. Other models are NOT copied to `usageHistory` by the trigger.

If the trigger is accidentally dropped:
```sql
CREATE TRIGGER auto_usage_log
AFTER INSERT ON requestDetails
WHEN NEW.model LIKE '%grok%' OR NEW.model LIKE '%mimo%' OR NEW.model LIKE '%free%'
BEGIN
    INSERT INTO usageHistory 
    (timestamp, provider, model, connectionId, apiKey, endpoint, promptTokens, completionTokens, cost, status, tokens, meta)
    VALUES (
        NEW.timestamp, COALESCE(NEW.provider, ''), NEW.model, COALESCE(NEW.connectionId, ''),
        '', '/v1/auto',
        COALESCE(json_extract(NEW.data, '$.tokens.prompt_tokens'), 0),
        COALESCE(json_extract(NEW.data, '$.tokens.completion_tokens'), 0),
        0.0, NEW.status,
        COALESCE(json_extract(NEW.data, '$.tokens'), '{}'), '{}'
    );
END;
```
