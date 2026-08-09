---
name: captcha-solving-services
description: Captcha solving APIs — 2captcha, Solverify, and local captcha-solver setup. Image captcha, reCAPTCHA Enterprise, Turnstile, Cloudflare clearance.
triggers:
  - captcha solver
  - 2captcha api
  - solverify api
  - recaptcha solving
  - image captcha ocr
  - cloudflare bypass
---

# Captcha Solving Services

## 2captcha API

### Image Captcha
```bash
# Upload
curl -X POST "https://2captcha.com/in.php" \
  -F "key=API_KEY" -F "method=base64" -F "body=<base64_image>" -F "json=1"
# Response: {"status":1,"request":"TASK_ID"}

# Poll (every 3-5 seconds)
curl "https://2captcha.com/res.php?key=API_KEY&action=get&id=TASK_ID&json=1"
# Response: {"status":1,"request":"SOLVED_CODE"} or {"status":0,"request":"CAPCHA_NOT_READY"}
```

### reCAPTCHA Enterprise
```bash
curl -X POST "https://2captcha.com/in.php" \
  -d "key=API_KEY" \
  -d "method=userrecaptcha" \
  -d "googlekey=SITEKEY" \
  -d "pageurl=https://target.com" \
  -d "enterprise=1" \
  -d "json=1"
```

### Balance Check
```bash
curl "https://2captcha.com/res.php?key=API_KEY&action=getbalance&json=1"
```

### Pitfalls
- Image captcha OCR quality varies by site:
  - **Xiaomi captchas**: ~30% accuracy on first attempt. 4-char codes are usually WRONG, 5-char codes are ~70% accurate. Use retry logic (skip 4-char, retry up to 5x) for ~95% success rate.
  - **Generic captchas**: ~60-70% accuracy
- reCAPTCHA Enterprise can be `ERROR_CAPTCHA_UNSOLVABLE` for hard sites
- Token expires ~2 minutes after solving — use immediately
- Polling interval: 3-5 seconds recommended
- `regsense=0` for case-insensitive matching (default)

## Solverify API

**Endpoint:** `https://solver.solverify.net/` (NOT `solverify.net` — that's the website, behind Cloudflare)

### Task Types (lowercase)
`turnstile`, `cloudflare_interstitial`, `perimeterx`, `datadome`, `akamai`, `aliyun`, `ocr`, `aws_waf`, `imperva`, `alix5sec`

**⚠️ Solverify does NOT support reCAPTCHA**

### Example: Turnstile
```bash
# Create task
curl -X POST "https://solver.solverify.net/createTask" \
  -H "Content-Type: application/json" \
  -d '{
    "clientKey": "API_KEY",
    "task": {
      "type": "turnstile",
      "websiteURL": "https://example.com",
      "websiteKey": "0x4AAAAAAAAYGKBMVPm3VNLY"
    }
  }'
# Response: {"errorId":0,"taskId":"UUID"}

# Poll result
curl -X POST "https://solver.solverify.net/getTaskResult" \
  -d '{"clientKey":"API_KEY","taskId":"UUID"}'
```

### Pitfalls
- Website `solverify.net` is behind Cloudflare — API at `solver.solverify.net` is accessible directly
- Task types are **lowercase** (`turnstile` not `TurnstileTaskProxyless`)
- Sitekey must match the domain it's configured for
- Only HTTP proxies accepted (not SOCKS5)
- **Status values**: `pending` → `processing` → `completed`/`failed` (NOT `ready` like 2captcha)
- **2captcha CANNOT solve Cloudflare Turnstile** — returns `ERROR_CAPTCHA_UNSOLVABLE`
- **Solverify Turnstile sitekey errors** (Error 110200): sitekey may be session-specific for some sites. Try `interstitial` type instead (requires residential proxy)
- **OpenAI/ChatGPT Cloudflare**: Extremely aggressive. Turnstile fails, Interstitial needs residential proxy. Manual login is the reliable fallback.
- **Interstitial type** returns `cf_clearance` cookie + browser cookies + useragent — requires proxy (datacenter IPs rejected)

### Sitekey Extraction (from browser console)
```javascript
performance.getEntriesByType('resource')
  .filter(e => e.name.includes('turnstile') || e.name.includes('challenge'))
  // Sitekey in URL: .../0x4AAAAAAADnPIDROrmt1Wwj/light/...
```

## Local Captcha Solver (self-hosted)

Installed at `/root/captcha-solver/` as systemd service `captcha-solver.service`.

### Supported Types
Turnstile, reCAPTCHA (v2/v3/Enterprise), hCaptcha, Cloudflare clearance, AWS WAF, BotGuard, DataDome, PerimeterX, Akamai, Aliyun

### Usage
```bash
# Health check
curl http://127.0.0.1:8877/health

# Solve Cloudflare
curl -X POST http://127.0.0.1:8877/solve \
  -H "Content-Type: application/json" \
  -d '{"type":"cloudflare","url":"https://protected.example.com","timeout_s":60}'

# Solve Turnstile
curl -X POST http://127.0.0.1:8877/solve \
  -d '{"type":"turnstile","sitekey":"0x4AAA...","url":"https://example.com"}'

# Solve reCAPTCHA Enterprise
curl -X POST http://127.0.0.1:8877/solve \
  -d '{"type":"recaptcha","version":"v2","enterprise":true,"sitekey":"6Lc...","url":"https://example.com"}'
```

### Management
```bash
systemctl status captcha-solver
systemctl restart captcha-solver
journalctl -u captcha-solver -f
```
