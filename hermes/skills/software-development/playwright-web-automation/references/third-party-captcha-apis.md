# Third-Party Captcha Solver APIs

Services like Solverify, CapSolver, Anti-Captcha, 2Captcha follow the same async pattern.

## Standard API Pattern

All use `createTask` → `getTaskResult` (polling) flow:

```
POST /createTask   → returns taskId
POST /getTaskResult → poll until status=ready, returns solution
POST /getBalance   → check account balance
```

Every request includes `clientKey` (API key).

## Solverify.net

**IMPORTANT: API endpoint is `solver.solverify.net`, NOT `solverify.net`!**
The website (`solverify.net`) is behind aggressive Cloudflare. The API subdomain is NOT.

- **API Base URL: `https://solver.solverify.net`**
- Docs: `https://solverify.net/docs` (website, blocked by CF from datacenter)
- The API subdomain works with plain curl — no Cloudflare bypass needed.
- Balance: confirmed working with `clientKey` in JSON body.

### Task types — ALL LOWERCASE (not PascalCase!)

| Task type | Description |
|-----------|-------------|
| `turnstile` | Cloudflare Turnstile → returns token in `solution.token` |
| `cloudflare_interstitial` | Cloudflare clearance → returns `cf_clearance` cookies |
| `perimeterx` | PerimeterX cookies + user-agent |
| `datadome` | DataDome validated cookie |
| `akamai` | Akamai Bot Manager cookies + sensor headers |
| `aliyun` | Aliyun Captcha 2.0 verification payload |
| `ocr` | Image-to-text from Base64 image |
| `aws_waf` | AWS WAF `aws-waf-token` cookie |
| `imperva` | Imperva/Incapsula cookies |
| `alix5sec` | Alibaba x5sec NoCaptcha |

### Request format
```json
{
  "clientKey": "API_KEY",
  "task": {
    "type": "turnstile",
    "websiteURL": "https://target.com",
    "websiteKey": "0x4AAAAAA..."
  }
}
```

### Response format
```json
// createTask
{"errorId": 0, "taskId": "abc123"}

// getTaskResult (processing)
{"errorId": 0, "status": "processing"}

// getTaskResult (ready)
{"errorId": 0, "status": "ready", "solution": {"token": "1.0eWQ2...", "userAgent": "..."}}

// Error — invalid sitekey/domain
{"errorId": 1, "errorCode": "ERROR_TASK_FAILED", "errorDescription": "Turnstile Error 110200 - Invalid sitekey or domain configuration"}

// Error — wrong task type
{"errorId": 1, "errorCode": "ERROR_INVALID_TASK", "errorDescription": "Invalid or missing task parameters"}
```

### Python client
```python
import json, time, urllib.request

API_KEY = "your-key"
BASE_URL = "https://solver.solverify.net"

def solve_turnstile(website_url, website_key, timeout=120):
    body = json.dumps({
        "clientKey": API_KEY,
        "task": {"type": "turnstile", "websiteURL": website_url, "websiteKey": website_key}
    }).encode()
    req = urllib.request.Request(f"{BASE_URL}/createTask", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())
    if result.get("errorId") != 0:
        return result
    task_id = result["taskId"]
    print(f"[*] Task created: {task_id}")

    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(5)
        body = json.dumps({"clientKey": API_KEY, "taskId": task_id}).encode()
        req = urllib.request.Request(f"{BASE_URL}/getTaskResult", data=body,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
        if result.get("errorId") != 0:
            return result
        if result.get("status") == "ready":
            return result
    raise TimeoutError(f"Solve timed out after {timeout}s")
```

## CapSolver

- Base URL: `https://api.capsolver.com`
- Same pattern as Solverify
- Task types: `AntiTurnstileTaskProxyLess`, `ReCaptchaV2TaskProxyLess`, etc.

## curl_cffi — Browser TLS Fingerprint

For calling APIs behind Cloudflare with browser-like TLS fingerprint:

```bash
pip install curl-cffi
```

```python
from curl_cffi import requests
session = requests.Session(impersonate="chrome131")
r = session.get("https://target.com", proxy="socks5://user:pass@host:port")
```

Mimics Chrome's JA3/JA4 TLS fingerprint. Won't solve JS challenges (use a real browser for that), but passes passive TLS fingerprint checks.

## Pitfalls

- **API vs website domain**: Solverify's API is at `solver.solverify.net`, not `solverify.net`. The website is behind Cloudflare; the API subdomain is not. Always check docs for the actual API hostname — don't assume the website domain is the API domain.
- **Task type casing**: Solverify uses lowercase (`turnstile`), NOT PascalCase (`TurnstileTaskProxyless`). Using wrong casing returns `ERROR_INVALID_TASK`. Other services (CapSolver) use PascalCase — always check docs.
- **Cloudflare on API websites**: Many solver service websites use Cloudflare. But their API subdomains often don't. Don't waste time trying to bypass CF on the website — find the actual API endpoint first.
- **Polling interval**: Don't poll faster than every 5s — most services rate-limit polling.
- **Token expiry**: Solved tokens are short-lived (typically 120s). Use immediately.
- **Error handling**: `errorId != 0` means task rejected. `ERROR_TASK_FAILED` = bad sitekey/domain config. `ERROR_INVALID_TASK` = wrong task type or missing params.
- **Invalid sitekey error 110200**: The sitekey doesn't match the domain. The sitekey must be registered for the exact `websiteURL` you pass. Demo/test sitekeys from docs may not work.
- **VPN Gate IPs also blocked**: Free VPN servers from VPN Gate are public and already flagged. Using VPNX doesn't help bypass CF on solver APIs. Residential proxies are the only reliable option from datacenter servers.
- **CloakBrowser vs regular Playwright**: CloakBrowser's anti-detect Chromium can bypass some CF challenges that regular Playwright cannot. But even CloakBrowser fails on aggressive CF without a residential IP.
- **Xiaomi captcha system**: Xiaomi uses reCAPTCHA Enterprise (verified 2026-07-17), NOT a custom system. Sitekey: `6LeBM0ocAAAAAEwYcFUjtxpVbs-0rnbSVXBBXmh4`. Solverify does NOT support reCAPTCHA — only Turnstile, Cloudflare Interstitial, PerimeterX, DataDome, Akamai, Aliyun, OCR, AWS WAF, Imperva, Alix5sec. Need CapSolver or 2captcha for reCAPTCHA Enterprise.
- **Solverify does NOT support reCAPTCHA**: Confirmed by testing all possible task type names (`recaptcha`, `recaptcha_v2`, `recaptcha_enterprise`, `RecaptchaV2EnterpriseTaskProxyless`, etc.) — all return `ERROR_INVALID_TASK`. Solverify's supported types are limited to the list in their docs.
