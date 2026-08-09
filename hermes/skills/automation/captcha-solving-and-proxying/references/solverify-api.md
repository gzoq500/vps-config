# Solverify API Reference

**Endpoint:** `https://solver.solverify.net/` (NOT `solverify.net`)

## Authentication
All requests include `clientKey` in the JSON body.

## Endpoints

### POST /getBalance
```json
{"clientKey": "YOUR_KEY"}
→ {"errorId": 0, "balance": 0.036}
```

### POST /createTask
```json
{
  "clientKey": "YOUR_KEY",
  "task": {
    "type": "turnstile",
    "websiteURL": "https://target.com",
    "websiteKey": "0x4AAAAAAA..."
  }
}
→ {"errorId": 0, "taskId": "uuid"}
```

### POST /getTaskResult
```json
{"clientKey": "YOUR_KEY", "taskId": "uuid"}
→ {"status": "processing"} or {"status": "ready", "solution": {...}}
```

## Task Types (all lowercase)
- `turnstile` — Cloudflare Turnstile
- `cloudflare_interstitial` — cf_clearance cookies
- `perimeterx` — PerimeterX cookies
- `datadome` — DataDome cookies
- `akamai` — Akamai cookies
- `aliyun` — Aliyun captcha
- `ocr` — Image to text
- `aws_waf` — AWS WAF token
- `imperva` — Imperva cookies
- `alix5sec` — Alibaba x5sec

## Pitfalls
- Task types are LOWERCASE (not CamelCase like CapSolver)
- Only `http` proxies accepted (not socks5)
- Does NOT support reCAPTCHA
- Test sitekeys may return `ERROR_TASK_FAILED`

## API Key
`9MRXGbCrXvdTVQLH6NtjFnhD6IjBlmSrpZLofsNkqGtVFOQFWGMrTtzX4aRCTGGD`
