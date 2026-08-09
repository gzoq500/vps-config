# Fresh Reinstall & Provider Restore

## When to Reinstall

When minified JS patches cause SyntaxError/crash and can't be reverted cleanly:
```bash
npm uninstall -g 9router && npm install -g 9router
```
**Database is preserved** — `/root/.9router/db/data.sqlite` survives uninstall.

## Provider Restore via Python (NOT SQL dump)

SQL `.dump` restore fails on fresh DB due to schema mismatch. Use Python:

```python
import sqlite3
orig = sqlite3.connect("/root/backup/data.sqlite")
new = sqlite3.connect("/root/.9router/db/data.sqlite")

# Copy providerNodes
for n in orig.execute("SELECT * FROM providerNodes").fetchall():
    new.execute("INSERT OR REPLACE INTO providerNodes VALUES (?,?,?,?,?,?)", n)

# Copy active custom providers only
for c in orig.execute("SELECT * FROM providerConnections WHERE provider LIKE 'openai-compatible%' AND isActive=1").fetchall():
    new.execute("INSERT OR REPLACE INTO providerConnections VALUES (?,?,?,?,?,?,?,?,?,?)", c)

# Copy active API keys
for k in orig.execute("SELECT * FROM apiKeys WHERE isActive=1").fetchall():
    new.execute("INSERT OR REPLACE INTO apiKeys VALUES (?,?,?,?,?,?)", k)

# Copy settings
for s in orig.execute("SELECT * FROM settings").fetchall():
    new.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", s)

# Copy kv (model aliases, custom models, pricing)
for k in orig.execute("SELECT * FROM kv").fetchall():
    new.execute("INSERT OR REPLACE INTO kv VALUES (?,?,?)", k)

new.commit()
```

## Usage Data Reset

To wipe usage data while keeping providers:
```python
new.execute("DELETE FROM usageHistory")
new.execute("DELETE FROM usageDaily")
new.execute("DELETE FROM requestDetails")
new.execute("DELETE FROM _meta WHERE key='totalRequestsLifetime'")
```

## Stream:false Token Tracking

Non-streaming requests capture real tokens. Streaming requests store 0.
To force non-streaming for Hermes: configure model with `stream:false`.

## Working Providers (July 2026)

| Prefix | Model | Tokens | Notes |
|--------|-------|--------|-------|
| `onerouter` | `qwen/qwen3.8-max-preview:free` | ✅ Real | Free, via OneRouter |
| `mimo` | `mimo-v2.5-pro` | ✅ Real | Via xiaomi-mimo |
| `tencent` | `hy3` | ⚠️ 0 | ORCAROUTER strips usage |
| `or` (OpenRouter) | `nvidia/nemotron-nano-12b-v2-vl:free` | N/A | Vision only, bypass 9Router |

## MiMo Pro Access

`mimo/mimo-v2.5-pro` routes through 9Router correctly with prefix `mimo`. Returns real token counts (257 in / 20 out confirmed). No vision support — use `mimo-v2.5` (not pro) for images.
