# Responses API Image Generation via9Router

## The Problem
Inferhub's `free/grok/grok-4.5` supports image generation, but ONLY via the `/v1/responses` endpoint with `tools: [{type: "image_generation"}]`. The `/v1/chat/completions` endpoint strips the `tools` parameter → empty response.

9Router's native logging only writes to `usageHistory` for `/v1/chat/completions`. `/v1/responses` entries appear in `requestDetails` but NOT `usageHistory` → invisible in dashboard RECENT REQUESTS.

## Working Image Gen Call
```python
import json, urllib.request, base64

key = 'sk-c60...'
model = 'openai-compatible-responses-a3e19181-5c72-46a6-8b66-b838ebaf2f17/free/grok/grok-4.5'

payload = {
    'model': model,
    'input': 'Generate image: a golden sunset tropical beach',
    'tools': [{'type': 'image_generation'}],
}
req = urllib.request.Request(
    'http://127.0.0.1:20128/v1/responses',
    data=json.dumps(payload).encode(),
    headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req, timeout=180) as resp:
    raw = resp.read()  # ~600KB-1MB
    # Parse first JSON object (response may be streamed)
    text = raw.decode('utf-8', 'replace')
    depth, end = 0, 0
    for i, c in enumerate(text):
        if c == '{': depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    d = json.loads(text[:end])
    for o in d.get('output', []):
        if isinstance(o, dict) and o.get('type') == 'image_generation_call':
            img_bytes = base64.b64decode(o['result'])
            with open('/root/generated.jpg', 'wb') as f:
                f.write(img_bytes)  # ~500-700KB JPEG
```

## Fix: SQLite Trigger for Auto-Logging
```sql
CREATE TRIGGER IF NOT EXISTS auto_usage_log
AFTER INSERT ON requestDetails
WHEN NEW.model LIKE '%grok%' OR NEW.model LIKE '%mimo%' OR NEW.model LIKE '%free%'
BEGIN
    INSERT INTO usageHistory 
    (timestamp, provider, model, connectionId, apiKey, endpoint, promptTokens, completionTokens, cost, status, tokens, meta)
    VALUES (
        NEW.timestamp,
        COALESCE(NEW.provider, ''),
        NEW.model,
        COALESCE(NEW.connectionId, ''),
        '',
        '/v1/auto',
        CASE WHEN COALESCE(json_extract(NEW.data, '$.tokens.prompt_tokens'), 0) > 0 
            THEN json_extract(NEW.data, '$.tokens.prompt_tokens') ELSE 200 END,
        CASE WHEN COALESCE(json_extract(NEW.data, '$.tokens.completion_tokens'), 0) > 0 
            THEN json_extract(NEW.data, '$.tokens.completion_tokens') ELSE 200 END,
        0.0,
        NEW.status,
        COALESCE((SELECT json_extract(NEW.data, '$.tokens')), '{}'),
        '{}'
    );
END;
```

## Fix: Patch route.js for Native Logging (preferred over trigger)
File: `/usr/local/lib/node_modules/9router/app/.next-cli-build/server/app/api/v1/responses/route.js`

**Why route.js patch over SQLite trigger:** 9router does NOT insert into `requestDetails` for `/v1/responses` calls at all. The SQLite trigger on `requestDetails` never fires for image gen. The route.js patch catches the response directly.

**Backup first:** `cp route.js route.js.bak`

Find: `async function j(a){return await h(),await (0,e.P)(a)}`

Replace with:
```javascript
async function j(a){await h();let r=await (0,e.P)(a);try{let b=require("node:path"),d=require("better-sqlite3"),p=b.join(process.env.HOME||"/root",".9router","db","data.sqlite"),db=new d(p),n=new Date().toISOString();db.prepare("INSERT INTO usageHistory(timestamp,provider,model,connectionId,apiKey,endpoint,promptTokens,completionTokens,cost,status,tokens,meta) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)").run(n,"inferhub","free/grok/grok-4.5","","","/v1/responses",200,200,0,"ok",JSON.stringify({prompt_tokens:200,completion_tokens:200}),"{}");db.close()}catch(e){}return r}
```

After patching: `systemctl restart 9router` (needed to reload route.js).

**Verify:**
```bash
sqlite3 ~/.9router/db/data.sqlite "SELECT timestamp,model FROM usageHistory WHERE model LIKE '%grok%' ORDER BY id DESC LIMIT 3"
```

**Caveat:** Hardcodes `provider='inferhub'` and `model='free/grok/grok-4.5'`. For other Responses API providers, detect provider from the request body.

## SQLite Trigger (alternative — only works if9router inserts into requestDetails)
The trigger below only fires if9router writes to `requestDetails` first. For `/v1/responses`, it does NOT — use the route.js patch above instead. The trigger is useful if9router adds native Responses API logging in a future version.

## Key Gotchas
- Response is huge (~800KB base64 JSON) — use streaming parse, not `json.loads(raw)`
- `image_generation_call` type in output array contains `result` (base64) and `prompt`
- Model must use full provider id: `openai-compatible-responses-<uuid>/free/grok/grok-4.5`
- Inferhub quota is shared/global — heavy image gen burns through it fast
-9router restart needed after route.js patch
