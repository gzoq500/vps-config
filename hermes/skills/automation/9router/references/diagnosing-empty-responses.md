# Diagnosing Empty Responses in 9Router

When a model returns empty content through9Router, the symptom is: "No reply: the model returned empty content after retries and any fallback providers."

## Step 1: Check Logs

```bash
journalctl -u 9router --no-pager -n 100
```

Look for patterns:
- `OUT 2-7` tokens with normal TTFT (thinking-only responses)
- `📊 DONE Xms · TTFT Yms · IN Z (CACHE ↻W) · OUT N` — low OUT = empty content
- `[Empty streaming response]` in request details
- `⚡ DISCONNECT: ResponseAborted` — client timeout during thinking

## Step 2: Query requestDetails SQLite

Database location: `~/.9router/db/data.sqlite`

### Find recent requests for a model:
```bash
DB=~/.9router/db/data.sqlite
sqlite3 "$DB" "SELECT * FROM requestDetails WHERE model LIKE '%MODEL_NAME%' ORDER BY rowid DESC LIMIT 5"
```

The output is pipe-delimited JSON. Key fields in the `data` column:
- `tokens.output_tokens` — if <10, response is likely empty
- `tokens.completion_tokens` — same metric
- `response.content` — "[Empty streaming response]" if empty
- `providerResponse` — raw provider response (may contain thinking blocks)
- `status` — "success" even if content is empty (HTTP 200)
- `latency.ttft` — time to first token (normal 5-15s for Claude)

### Parse with jq:
```bash
sqlite3 "$DB" "SELECT data FROM requestDetails WHERE model='claude-fable-5' ORDER BY rowid DESC LIMIT 1" | jq '.tokens, .response.content, .providerResponse[:200]'
```

## Step 3: Check Provider Auth

```bash
# List all providers
sqlite3 "$DB" "SELECT id, provider, name, isActive, priority FROM providerConnections"

# Check specific provider auth (e.g., Claude)
sqlite3 "$DB" "SELECT json_extract(data, '$.expiresAt'), json_extract(data, '$.lastError'), json_extract(data, '$.isActive') FROM providerConnections WHERE provider='claude'"
```

Auth fields:
- `expiresAt` — ISO timestamp; if past, token is expired
- `lastError` — last error message (null if clean)
- `isActive` — 1 = enabled, 0 = disabled

## Step 4: Identify Root Cause

### Pattern A: Thinking-Only Responses
**Symptoms:** `output_tokens: 2-7`, TTFT normal, `providerResponse: "[Empty streaming response]"`
**Cause:** Model generates thinking tokens but returns empty content block. Happens with:
- Extended thinking enabled (`THINK:8k` budget)
- Large context (100K+ tokens)
- Non-standard model names that may not handle thinking correctly

**Fix:**
1. Disable thinking for the model (if configurable in provider settings)
2. Reduce context size (compact conversation in Hermes: `/compact`)
3. Switch to standard model name (e.g., `claude-sonnet-4` instead of `claude-fable-5`)
4. Increase `max_tokens` in the request

### Pattern B: Auth Issues
**Symptoms:** `401`, `403`, or `No credentials for provider`
**Cause:** Token expired, wrong key, or provider disabled

**Fix:**
1. Check `expiresAt` in `providerConnections.data`
2. Re-authenticate via dashboard
3. Verify `isActive=1` for the provider

### Pattern C: Format Conversion Issues
**Symptoms:** Works with direct API but fails through9Router
**Cause:** `openai→claude` or `openai→openai` format conversion not handling response correctly

**Fix:**
1. Test direct API call (bypass9Router) to confirm model works
2. Check if model requires specific format (some models need `stream:true`)
3. Try different `apiType` in provider config

### Pattern D: Large Context
**Symptoms:** Works for short conversations, fails for long ones
**Cause:** Model context window exceeded or model returns minimal output for large contexts

**Fix:**
1. Compact conversation in Hermes
2. Use model with larger context window
3. Split conversation into smaller chunks

## Step 5: Verify Fix

After applying fix, test with a simple request:
```bash
curl -s -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"MODEL_NAME","messages":[{"role":"user","content":"Reply exactly: OK"}],"max_tokens":20,"stream":false}' \
  "http://127.0.0.1:20128/v1/chat/completions"
```

Check response has non-empty `choices[0].message.content`.

## Quick Reference: SQLite Tables

| Table | Purpose |
|-------|---------|
| `providerConnections` | Auth credentials per provider |
| `providerNodes` | Custom providers (Inferhub, etc.) |
| `requestDetails` | Full request/response logs |
| `usageDaily` | Token usage per day |
| `apiKeys` | Dashboard API keys |
| `settings` | Global settings (password, strategies) |
| `combos` | Model routing rules |
| `kv` | Key-value store (customModels, etc.) |
