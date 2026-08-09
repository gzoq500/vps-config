# Patching9router for Responses API Logging

## Problem
9router's native logging (`usageHistory` + `requestDetails`) only fires for `/v1/chat/completions`. Calls to `/v1/responses` (image gen) bypass logging entirely — invisible in dashboard.

SQLite triggers on `requestDetails` do NOT help because9router doesn't insert into that table for Responses API calls.

## Solution: Patch `route.js`

File: `/usr/local/lib/node_modules/9router/app/.next-cli-build/server/app/api/v1/responses/route.js`

Find the POST handler in module 83122:
```js
async function j(a){return await h(),await (0,e.P)(a)}
```

Replace with a wrapper that logs to usageHistory after the response:
```js
async function j(a){await h();let r=await (0,e.P)(a);try{let b=require("node:path"),d=require("better-sqlite3"),p=b.join(process.env.HOME||"/root",".9router","db","data.sqlite"),db=new d(p),n=new Date().toISOString();db.prepare("INSERT INTO usageHistory(timestamp,provider,model,connectionId,apiKey,endpoint,promptTokens,completionTokens,cost,status,tokens,meta) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)").run(n,"inferhub","free/grok/grok-4.5","","","/v1/responses",200,200,0,"ok",JSON.stringify({prompt_tokens:200,completion_tokens:200}),"{}");db.close()}catch(e){}return r}
```

## Notes
- `better-sqlite3` is available in9router's node_modules (used by the main DB layer)
- Token counts are hardcoded estimates (200/200) since Responses API doesn't return usage
- After patching, restart9router: `systemctl restart 9router`
- This patch is lost on9router update (`npm update -g 9router`) — re-apply after updates
- The model/provider values should match the actual connection being used
- For dynamic provider detection, parse the request body's `model` field and look up the connection from DB

## Alternative: Proxy approach
Instead of patching9router source, run a lightweight proxy on a separate port (e.g.20129) that:
1. Forwards all requests to9router :20128
2. For `/v1/responses` requests, logs to usageHistory after the response
3. All clients point to the proxy port

This survives9router updates but adds another process.

## Verified
- Patch applied to9router v0.5.40 on Ubuntu22.04
- Image gen via `POST /v1/responses` with `tools:[{type:"image_generation"}]` now appears in dashboard
- Restart required after patching (Next.js caches routes)
