# Add Provider via9Router Internal API (browser_console)

When SQLite inserts fail to sync with the routing engine (pitfall #51/75) and the Web UI Create button silently no-ops (pitfall #77), use this approach.

## Prerequisites
- Dashboard is open in browser (authenticated session)
- Provider API endpoint is reachable from9Router host
- Upstream API key is valid

## Step 1: Create Provider Node

```js
// Run in browser_console
(async () => {
  const resp = await fetch('/api/provider-nodes', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      type: 'openai-compatible',   // MUST be exactly this, NOT 'openai-compatible-chat'
      name: 'XKiro',               // Display label
      prefix: 'xkiro',             // Single-segment prefix (pitfall #6)
      apiType: 'chat',
      baseUrl: 'https://api.xkiro.com/v1'
    })
  });
  const data = await resp.json();
  return JSON.stringify({status: resp.status, nodeId: data.node?.id, body: data});
})()
```

Expected: status 201, node ID format `openai-compatible-chat-<uuid>`

## Step 2: Add Connection (API Key)

```js
(async () => {
  const nodeId = 'openai-compatible-chat-<uuid-from-step-1>';
  const resp = await fetch('/api/providers', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      provider: nodeId,              // UUID from step 1
      name: 'XKiro1',               // Connection name
      apiKey: 'sk-xt-...',          // Upstream provider key
      defaultModel: 'xiaomi/mimo-v2.5-pro:free'
    })
  });
  const data = await resp.json();
  return JSON.stringify({status: resp.status, connId: data.connection?.id, body: data});
})()
```

Expected: status 201, connection ID format `<uuid>`

## Step 3: Fix testStatus (Dashboard Badge)

The API creates connections with `testStatus: "unknown"` (gray badge). To make the dashboard show green:

```bash
DB=~/.9router/db/data.sqlite
sqlite3 "$DB" "UPDATE providerConnections SET data=json_set(data, '$.testStatus', 'active', '$.errorCode', null, '$.lastError', null, '$.lastErrorAt', null, '$.backoffLevel', 0) WHERE id='<conn-id-from-step-2>';"
```

Then restart 9Router for the badge to update.

## Step 4: Verify

```bash
# From terminal
curl -s http://localhost:<port>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"xkiro/<model-id>","messages":[{"role":"user","content":"Hi"}],"max_tokens":50}'
```

If `No active credentials for provider: xkiro` → restart9Router and retry.
If upstream 401 → test upstream directly: `curl -s <baseUrl>/models -H "Authorization: Bearer <key>"`

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `Invalid provider node type` | Wrong type field | Use `openai-compatible` not `openai-compatible-chat` |
| `Prefix is required` | Missing prefix field | Add `prefix: 'xkiro'` to body |
| `API Key is required` | Missing apiKey in connection | Add `apiKey` field to step 2 body |
| `Connection not found` | Wrong method/endpoint | Step 2 uses POST to `/api/providers`, not PUT |
| `Unauthorized` | Not in browser session | Run from browser_console, not terminal curl |

## Why This Works When SQLite Doesn't

SQLite inserts bypass9Router's internal registration logic. The API POST approach goes through the same code path as the Web UI, which properly:
1. Registers the node in the routing engine's in-memory cache
2. Links the connection to the node with correct foreign key resolution
3. Triggers model discovery from the upstream `/models` endpoint

Raw SQLite inserts may leave the routing engine stale until a full restart with cache invalidation — which doesn't always happen cleanly.
