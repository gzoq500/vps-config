# Cloudflare API Management for TempMail

## Auth
```python
headers = {"X-Auth-Email": CF_EMAIL, "X-Auth-Key": CF_KEY}
# CF_KEY = Global API Key from dash.cloudflare.com/profile/api-tokens
# Account ID visible in dashboard URL after /edd4541...
```

## Get Zone ID
```python
r = requests.get(f"https://api.cloudflare.com/client/v4/zones?name={domain}", headers=headers)
zone_id = r.json()['result'][0]['id']
```

## DNS Records
```python
# List all records
r = requests.get(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records", headers=headers)

# Add A record (DNS only - for direct subdomain)
requests.post(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records", headers=headers, json={
    "type": "A", "name": "direct", "content": "43.167.12.204", "ttl": 1, "proxied": False
})

# Add A record (proxied - for web)
requests.post(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records", headers=headers, json={
    "type": "A", "name": "mail", "content": "43.167.12.204", "ttl": 1, "proxied": False
})

# Delete record
requests.delete(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}", headers=headers)
```

## Email Routing
```python
# Get routing rules
r = requests.get(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/email/routing/rules", headers=headers)
for rule in r.json()['result']:
    print(rule['tag'], rule['actions'], rule['enabled'])

# Enable Email Routing
requests.patch(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/email/routing", headers=headers, json={"enabled": True})
```

## Worker Deployment (modules format)
```python
# Deploy Worker script
files = {
    'index.js': ('index.js', script.encode(), 'application/javascript+module'),
    'metadata': ('metadata', json.dumps({"main_module": "index.js"}).encode(), 'application/json'),
}
r = requests.put(
    f"https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/scripts/{worker_name}",
    headers={"X-Auth-Email": CF_EMAIL, "X-Auth-Key": CF_KEY},
    files=files, timeout=30
)

# Get Worker settings
r = requests.get(f"https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/scripts/{worker_name}/settings", headers=headers)

# Update Worker settings (enable observability)
requests.patch(f"https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/scripts/{worker_name}/settings", headers=headers, json={
    "observability": {"enabled": True, "logs": {"enabled": True, "head_sampling_rate": 1, "persist": True}}
})
```

## Key Gotchas
- Worker deployment requires `main_module` metadata (not `body_part`)
- File content-type must be `application/javascript+module` (not `application/javascript`)
- Email handler only works with modules format (not service-worker `addEventListener`)
- Global API Key gives full access - scope API Tokens for production use
- DNS changes propagate within seconds to Cloudflare resolvers, but ISP/phone caches may take hours
