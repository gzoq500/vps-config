# Cloudflare Worker for Email Routing → TempMail API

## Problem
VPS providers (Tencent, AWS, GCP) block inbound port 25. External emails from Gmail/outlook never reach Postfix.

## Solution
Use Cloudflare Email Routing + Worker to bridge inbound emails to TempMail API.

## Working Architecture
```
Gmail → Cloudflare MX (route1/2/3.mx.cloudflare.net)
  → Cloudflare Worker (calm-sea-5842)
    → fetch POST https://direct.routerssh.web.id/api/incoming
      → Caddy (DNS-only A record) → port 3001 C++ backend
        → SQLite + /var/mail/admin mbox
```

## Worker Code (modules format)

```javascript
export default {
  async email(message, env, ctx) {
    const from = message.from || "unknown";
    const to = message.to || "unknown";
    const subject = message.headers.get("subject") || "(No subject)";
    let body = "";
    try {
      const raw = await new Response(message.raw).text();
      const idx = raw.indexOf("\r\n\r\n");
      body = idx !== -1 ? raw.substring(idx + 4) : raw;
    } catch(e) {
      body = "(read error)";
    }
    try {
      const resp = await fetch("https://direct.routerssh.web.id/api/incoming", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({from, to, subject, body, html: body})
      });
      console.log("OK", resp.status, from, "->", to);
    } catch(e) {
      console.error("FAIL", e.message);
    }
  }
}
```

## Deploy via Cloudflare API (no browser needed)

```python
import requests, json

CF_EMAIL = "your@email.com"
CF_KEY = "your-global-api-key"  # from dash.cloudflare.com/profile/api-tokens
ACCOUNT = "your-account-id"     # from dashboard URL
WORKER = "your-worker-name"

url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT}/workers/scripts/{WORKER}"

script = open("worker.js").read()
metadata = json.dumps({"main_module": "index.js", "bindings": [], "compatibility_date": "2025-05-23"})

files = {
    'index.js': ('index.js', script.encode(), 'application/javascript+module'),
    'metadata': ('metadata', metadata.encode(), 'application/json'),
}

headers = {"X-Auth-Email": CF_EMAIL, "X-Auth-Key": CF_KEY}
r = requests.put(url, headers=headers, files=files, timeout=30)
print(r.json())
```

## Setup Email Routing via API

```python
# Get zone ID
r = requests.get(f"https://api.cloudflare.com/client/v4/zones?name={DOMAIN}",
    headers=headers, timeout=15)
zone_id = r.json()['result'][0]['id']

# Check current routing rules
r = requests.get(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/email/routing/rules",
    headers=headers, timeout=15)
print(r.json())
```

## Setup Steps (Dashboard or API)
1. DNS → delete old MX record (e.g., `mail.domain → IP`)
2. DNS → add `direct.domain → SERVER_IP` (DNS only, NOT proxied)
3. Email Routing → Settings → "Add missing records" (adds Cloudflare MX)
4. Destination Addresses → add your Gmail
5. Routing Rules → Catch-all → "Send to Worker" → select your Worker
6. Deploy Worker code (API or dashboard)
7. Caddy config: add `direct.domain` site block to proxy `/api/*` to `localhost:3001`

## Key Pitfalls (learned from production)

### ✅ PROVEN WORKING pattern:
- DNS-only A record `direct.domain → IP` bypasses Cloudflare proxy
- Worker fetches `https://direct.domain/api/incoming` (HTTPS, standard port)
- Caddy on port 80/443 reverse-proxies to backend port 3001
- Backend writes to BOTH SQLite AND `/var/mail/admin` mbox

### ❌ What DOESN'T work:
1. **`http://IP:3001`** from Worker → returns 403 (non-standard port, HTTP)
2. **`https://tempmail.domain/api/incoming`** → silent failure (Cloudflare proxy loop)
3. **`http://direct.domain:3001`** → Worker can't reach non-standard ports via HTTP
4. **Catch-all wildcard `*`** in email pattern field → not accepted characters
5. **Existing MX records** conflict with Cloudflare MX → delete old first
6. **Worker modules format required** for `email` handler (not service-worker)
7. **Postfix `mydestination`** with domain + transport_maps conflict → use transport_maps override

### Worker deploy metadata format:
```python
files = {
    'index.js': ('index.js', script.encode(), 'application/javascript+module'),
    'metadata': ('metadata', json.dumps({"main_module": "index.js"}).encode(), 'application/json'),
}
# PUT to /accounts/{ACCOUNT}/workers/scripts/{WORKER}
```

### Caddy config for direct subdomain (MUST use http:// prefix):
```
http://direct.routerssh.web.id {
    reverse_proxy /api/* localhost:3001
}
```
**Without `http://` prefix**, Caddy auto-upgrades to HTTPS and returns 308 redirects that break Worker POST requests. Always use explicit `http://` for the direct subdomain.
