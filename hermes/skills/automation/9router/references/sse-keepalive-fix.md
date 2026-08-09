# SSE Keepalive Fix — Confirmed Working Pattern

## Problem
9Router SSE `/api/usage/stream` keepalive only sends `: ping` comment every 25s. Dashboard doesn't auto-update because event emitter only fires on `DONE` status (streaming `ResponseAborted` requests never trigger it).

## Fix (stream/route.js)
Replace the ping-only keepalive with a stats update. Use IIFE inside setInterval (NOT async arrow):

```javascript
// Original:
controller.enqueue(encoder.encode(": ping\n\n"));
// ...interval: 25000

// Fixed:
(async()=>{
  try{
    let d;
    try{d=await(0,v.BY)("today")}catch{d=null}
    if(d){
      state.cachedStats=d;
      controller.enqueue(encoder.encode(`data: ${JSON.stringify(d)}\n\n`));
    } else {
      controller.enqueue(encoder.encode(": ping\n\n"));
    }
  }catch{
    try{controller.enqueue(encoder.encode(": ping\n\n"))}catch{state.closed=true;clearInterval(state.keepalive)}
  }
})()
// ...interval: 10000
```

## Key Rules
1. Use `(async()=>{...})()` IIFE — NOT `async () => {}` as setInterval callback
2. Call `BY("today")` — NOT `BY()` (hangs on large tables)
3. Fallback to `: ping` on any error
4. Interval: 10000ms (10s) — not 25000ms
5. Only send stats data, NOT recentRequests (causes flicker)

## What NOT to do
- Do NOT make setInterval itself async
- Do NOT send recentRequests in keepalive (causes UI flicker)
- Do NOT call BY() without "today" param (queries 6000+ rows → hang)
- Do NOT patch chunk 4884.js for this — only patch stream/route.js
