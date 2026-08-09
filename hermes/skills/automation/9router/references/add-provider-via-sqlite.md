# Add OpenAI-Compatible Provider via SQLite (Proven Recipe)

When the Web UI is inaccessible or you need to script provider addition, use direct SQLite.

## Key Insight

`providerConnections.provider` must reference a **providerNodes UUID**, not the type string.
Setting it to just `openai-compatible-chat` causes: `No active credentials for provider: <prefix>`.

## Database Schema

```sql
-- providerNodes: defines the upstream endpoint
CREATE TABLE providerNodes (
  id TEXT PRIMARY KEY,        -- e.g. "openai-compatible-chat-da6f81c4"
  type TEXT,                  -- "openai-compatible"
  name TEXT,                  -- display name e.g. "OneRouter"
  data TEXT NOT NULL,         -- JSON: {prefix, apiType, baseUrl}
  createdAt TEXT NOT NULL,
  updatedAt TEXT NOT NULL
);

-- providerConnections: credentials linked to a node
CREATE TABLE providerConnections (
  id TEXT PRIMARY KEY,        -- UUID
  provider TEXT,              -- MUST match providerNodes.id (not the type!)
  authType TEXT,              -- "apikey"
  name TEXT,                  -- display name
  email TEXT,
  priority INTEGER DEFAULT 0,
  isActive INTEGER DEFAULT 1,
  data TEXT,                  -- JSON: {apiKey, defaultModel, testStatus, providerSpecificData}
  createdAt TEXT NOT NULL,
  updatedAt TEXT NOT NULL
);

-- apiKeys: 9Router's own keys for clients
CREATE TABLE apiKeys (
  id TEXT PRIMARY KEY,
  key TEXT UNIQUE NOT NULL,   -- the actual sk-... key clients use
  name TEXT,
  machineId TEXT,
  isActive INTEGER DEFAULT 1,
  createdAt TEXT NOT NULL
);
```

## Working Python Recipe

```python
import sqlite3, json, uuid
from datetime import datetime, timezone

DB = "/root/.9router/db/data.sqlite"
conn = sqlite3.connect(DB)
cur = conn.cursor()
now = datetime.now(timezone.utc).isoformat()

# 1. Create providerNode
node_id = "openai-compatible-chat-" + uuid.uuid4().hex[:8]
node_data = {
    "prefix": "onerouter",          # single-segment! (pitfall #6)
    "apiType": "chat",
    "baseUrl": "https://llm.onerouter.pro/v1"
}
cur.execute("""
    INSERT INTO providerNodes (id, type, name, data, createdAt, updatedAt)
    VALUES (?, ?, ?, ?, ?, ?)
""", (node_id, "openai-compatible", "OneRouter", json.dumps(node_data), now, now))

# 2. Create providerConnection linked to that node
conn_id = str(uuid.uuid4())
conn_data = {
    "defaultModel": "qwen/qwen3.8-max-preview:free",
    "apiKey": "sk-...",             # upstream provider key
    "testStatus": "active",         # must be "active" not "untested"
    "errorCode": None,
    "backoffLevel": 0,
    "lastError": None,
    "lastErrorAt": None,
    "providerSpecificData": {
        "prefix": "onerouter",
        "apiType": "chat",
        "baseUrl": "https://llm.onerouter.pro/v1",
        "nodeName": "OneRouter",
        "connectionProxyEnabled": False,
        "connectionProxyUrl": "",
        "connectionNoProxy": ""
    }
}
cur.execute("""
    INSERT INTO providerConnections (id, provider, authType, name, email, priority, isActive, data, createdAt, updatedAt)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (conn_id, node_id, "apikey", "OneRouter", None, 0, 1, json.dumps(conn_data), now, now))

conn.commit()
conn.close()
```

## After Insert

```bash
systemctl restart 9router
sleep 3

# Get 9Router's own API key
API_KEY=$(sqlite3 ~/.9router/db/data.sqlite "SELECT key FROM apiKeys WHERE isActive=1 LIMIT 1")

# Test
curl -s -X POST "http://localhost:20128/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"model":"onerouter/qwen/qwen3.8-max-preview:free","messages":[{"role":"user","content":"test"}],"stream":false}'
```

## Model Naming

With prefix `onerouter`, call models as: `onerouter/<upstream-model-id>`
Example: `onerouter/qwen/qwen3.8-max-preview:free`

## Common Failures

| Error | Cause | Fix |
|-------|-------|-----|
| `Missing API key` | No `Authorization` header with 9Router key | Add `Bearer <apiKeys.key>` |
| `No active credentials for provider: X` | `providerConnections.provider` is type string not node UUID | Create providerNodes row, link UUID |
| `No active credentials` (still) | `testStatus` is `"untested"` | Set to `"active"` |
| Model not found | Wrong prefix or model id | Use `<prefix>/<exact-upstream-model-id>` |
