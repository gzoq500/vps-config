# 9Router API & Dashboard Tricks

## Creating Providers via Browser Console

Dashboard "Create" button silently fails when "Default Model" validation fails. Use browser console API instead:

```javascript
// 1. Create node
const resp = await fetch('/api/provider-nodes', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    name: 'Keelcode',
    prefix: 'kx',
    type: 'openai-compatible',
    apiType: 'chat',
    baseUrl: 'http://PUBLIC_IP:3456/v1'
  })
});
// Returns: {node: {id: "openai-compatible-chat-UUID", ...}}

// 2. Update node if needed
await fetch('/api/provider-nodes/' + nodeId, {
  method: 'PUT',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({name:'Keelcode', apiType:'chat', baseUrl:'http://NEW_URL/v1'})
});

// 3. Add connection via DB (no API endpoint for connections)
```

## Adding Connections via DB

No API endpoint exists for providerConnections. Insert directly:

```python
import sqlite3, json, uuid, datetime
db = sqlite3.connect('/root/.9router/db/data.sqlite')
cur = db.cursor()
NOW = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')
conn_id = str(uuid.uuid4())
cur.execute("INSERT INTO providerConnections VALUES (?,?,?,?,?,?,?,?,?)",
  (conn_id, 'Connection1', nodeId, 1, 1, json.dumps({
    "apiKey": "YOUR_KEY",
    "defaultModel": "gpt-4o-mini",
    "priority": 1,
    "isActive": True
  }), NOW, NOW, True))
db.commit()
# MUST restart after: systemctl restart 9router
```

## requireApiKey

9Router dashboard has "Require API key" toggle (Endpoint page). When ON:
- ALL requests to `localhost:20128` need `Authorization: Bearer <key>`
- Keys visible in dashboard Endpoint page
- Do NOT disable — use the key

## Finding Turnstile Sitekey

For Cloudflare-protected sites, extract sitekey from browser console:
```javascript
const perf = performance.getEntriesByType('resource');
const cf = perf.filter(e => e.name.includes('turnstile') || e.name.includes('challenge'));
// Sitekey is in URL like: .../0x4AAAAAAADnPIDROrmt1Wwj/light/...
```

## Model List

9Router only shows models from providers with active connections. Custom providers appear with prefix:
```
kx/kimi-k3, kx/deepseek-v4-flash, kx/gpt-5.6-sol, etc.
```
