# 9Router SSRF Protection (v0.5.50, August 2026)

## Problem
9Router blocks HTTP requests to private/reserved IP ranges when routing to custom provider baseUrl. The proxy never receives the request —9Router silently drops it and may fall back to direct upstream (producing confusing auth errors).

## Blocked Ranges
```
0.0.0.0/8
10.0.0.0/8
127.0.0.0/8
169.254.0.0/16
172.16.0.0/12
192.168.0.0/16
```
Also blocks: `localhost`, `ip6-localhost`, `ip6-loopback`

## Source Location
In `app/.next-cli-build/server/app/api/provider-nodes/validate/route.js`:
```javascript
let g = [
  [f("0.0.0.0"), 8],
  [f("10.0.0.0"), 8],
  [f("127.0.0.0"), 8],
  [f("169.254.0.0"), 16],
  [f("172.16.0.0"), 12],
  [f("192.168.0.0"), 16),
];
// ... validation checks hostname against these ranges
// Returns "Blocked URL: internal host" if matched
```

## Solution
1. Local proxy MUST bind to `0.0.0.0` (all interfaces), NOT `127.0.0.1`
2. Provider node baseUrl MUST use the VPS public IP: `http://<PUBLIC_IP>:<PORT>/v1`
3. Public IPs (e.g. `209.127.114.234`) are NOT in blocked ranges

## Verification
```bash
# WRONG — proxy on localhost, 9Router blocks
curl http://localhost:20128/v1/chat/completions -d '{"model":"kx/test",...}'
# → 401 from upstream (9Router bypassed proxy)

# CORRECT — proxy on public IP, 9Router routes through it
curl http://localhost:20128/v1/chat/completions -d '{"model":"kx/test",...}'
# → proxy receives request, translates, forwards
```

## Applies To
- Any local translation proxy (OpenAI→Anthropic, header injection, etc.)
- AgentRouter proxy
- Custom middleware proxies
- NOT applicable when provider is a remote API (no SSRF issue)
