---
name: captcha-solving-pipeline
type: reference
---

# Captcha Solving Pipeline

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ Target Site │────▶│ Captcha Type │────▶│   Solver    │
│  (Xiaomi)   │     │  Detection   │     │  Selection  │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                    ┌───────────────────────────┤
                    ▼               ▼           ▼
              ┌──────────┐   ┌──────────┐  ┌──────────┐
              │ 2captcha │   │ Solverify│  │  Local   │
              │   API    │   │   API    │  │ Captcha- │
              │          │   │          │  │  Solver  │
              └──────────┘   └──────────┘  └──────────┘
```

## 2captcha API

### Image Captcha
```bash
# Upload
curl -X POST "https://2captcha.com/in.php" \
  -d "key=API_KEY" -d "method=base64" \
  -d "body=BASE64_IMAGE" -d "json=1"
# Response: {"status":1,"request":"TASK_ID"}

# Poll
curl "https://2captcha.com/res.php?key=API_KEY&action=get&id=TASK_ID&json=1"
# Response: {"status":1,"request":"SOLVED_CODE"}
```

### reCAPTCHA Enterprise
```bash
curl -X POST "https://2captcha.com/in.php" \
  -d "key=API_KEY" -d "method=userrecaptcha" \
  -d "googlekey=SITEKEY" -d "pageurl=PAGE_URL" \
  -d "enterprise=1" -d "json=1"
```

### File Upload (alternative)
```bash
curl -X POST "https://2captcha.com/in.php" \
  -F "file=@captcha.jpg" \
  -d "key=API_KEY" -d "json=1"
```

### Balance Check
```bash
curl "https://2captcha.com/res.php?key=API_KEY&action=getbalance&json=1"
```

## Solverify API

**Endpoint**: `https://solver.solverify.net/` (NOT `solverify.net`)

### Task Types
- `turnstile` — Cloudflare Turnstile
- `cloudflare_interstitial` — CF clearance cookies
- `perimeterx` — PerimeterX cookies
- `datadome` — DataDome cookies
- `akamai` — Akamai cookies
- `aliyun` — Aliyun Captcha 2.0
- `ocr` — Image to text

**Does NOT support reCAPTCHA** — use 2captcha for that.

### Usage
```python
# Create task
r = requests.post("https://solver.solverify.net/createTask", json={
    "clientKey": "API_KEY",
    "task": {"type": "turnstile", "websiteURL": "https://target.com", "websiteKey": "SITEKEY"}
})
task_id = r.json()["taskId"]

# Poll
r = requests.post("https://solver.solverify.net/getTaskResult", json={
    "clientKey": "API_KEY", "taskId": task_id
})
# status: "processing" | "ready"
```

## Local Captcha Solver (port 8877)

```bash
# Health check
curl http://127.0.0.1:8877/health

# Solve Cloudflare
curl -X POST http://127.0.0.1:8877/solve -H 'Content-Type: application/json' \
  -d '{"type":"cloudflare","url":"https://target.com","timeout_s":60}'

# Solve reCAPTCHA
curl -X POST http://127.0.0.1:8877/solve -H 'Content-Type: application/json' \
  -d '{"type":"recaptcha","version":"v2","sitekey":"KEY","url":"https://target.com"}'
```

## Xiaomi-Specific Captcha Flow

1. **Trigger**: Send request without captcha → server returns `captchaUrl`
2. **Get**: `GET captchaUrl` → captcha image (JPEG, 125x42px)
3. **Solve**: Upload to 2captcha, poll for result
4. **Submit**: Re-send request with captcha code in `icode` field

**Pitfall**: The `register` type captcha (`icodeType=register`) has poor OCR accuracy on 2captcha. The `login` type (`icodeType=login`) works reliably.

**Pitfall**: Captcha codes expire quickly. Get and use in same session, minimal delay.

**Pitfall**: Xiaomi rate-limits email sends (error `20332`). Limit ~4-5 emails/hour per address. Wait ~1 hour or use different email.

**Pitfall**: `register` captcha type has ~20-30% OCR accuracy on 2captcha. May need 3-5 retries.

**Pitfall**: The `captchaToken` cookie (set after successful `sendEmailRegTicket`) is NOT a reliable verification ticket. It works ~50% of the time with `verifyEmailRegTicket`, but often returns `70014` (verification code error). Always use the actual email verification code as the `ticket` parameter for reliable automation.

## VPNX Proxy

Self-hosted rotating VPN proxy via Docker:
```bash
docker run -d --name vpnx --cap-add=NET_ADMIN --device=/dev/net/tun \
  -p 1080:1080 -p 8080:8080 -p 8000:8000 \
  -e API_TOKEN=SECRET vpnx:local

# Connect
curl -X POST http://localhost:8000/connect -H "Authorization: Bearer SECRET"

# Use proxy
curl --socks5 user:pass@localhost:1080 https://ifconfig.me
```

Note: VPN Gate free servers are datacenter IPs — Cloudflare blocks them. Use residential proxy for CF-protected sites.
