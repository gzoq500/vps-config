---
name: captcha-solving-and-proxying
description: "Captcha solving services, self-hosted solvers, proxy infrastructure for bypassing bot protection (Cloudflare, GeeTest, reCAPTCHA, DataDome, etc.)"
triggers:
  - captcha solving
  - bypass Cloudflare
  - bot protection
  - rotating proxy
  - SOCKS5 proxy
  - VPN proxy
  - reCAPTCHA solver
  - GeeTest
  - cf_clearance
---

# Captcha Solving & Proxy Infrastructure

## Solverify API (Cloud Service)

**Endpoint:** `https://solver.solverify.net/` (NOT `solverify.net` — the website domain is behind Cloudflare and blocks API calls)

**Auth:** `clientKey` field in every request body.

**Async flow:**
1. `POST /createTask` → returns `taskId`
2. Poll `POST /getTaskResult` with `taskId` → `status: "processing"` then `"ready"`
3. `POST /getBalance` → `{errorId: 0, balance: 0.036}`

**Task types are LOWERCASE** (not CamelCase like CapSolver):
- `turnstile` — Cloudflare Turnstile token
- `cloudflare_interstitial` — cf_clearance cookies
- `perimeterx`, `datadome`, `akamai`, `aliyun`, `ocr`, `aws_waf`, `imperva`, `alix5sec`

**Common pitfalls:**
- Using `TurnstileTaskProxyless` (CapSolver style) → `ERROR_INVALID_TASK`. Use `turnstile` instead.
- Using `solverify.net` as API endpoint → Cloudflare 403. Use `solver.solverify.net`.
- Test sitekeys like `0x4AAAAAAAABnWw3L9QK5n3h` may return `ERROR_TASK_FAILED: Invalid sitekey`. Use real sitekeys from target sites.
- Only `http` proxies accepted by proxy-based task types (not socks5).
- **Solverify does NOT support reCAPTCHA** — only Turnstile, Cloudflare Interstitial, PerimeterX, DataDome, Akamai, Aliyun, OCR, AWS WAF, Imperva, Alix5sec. For reCAPTCHA, use 2captcha or Anti-Captcha.

**API key used:** `9MRXGbCrXvdTVQLH6NtjFnhD6IjBlmSrpZLofsNkqGtVFOQFWGMrTtzX4aRCTGGD`

## Captcha-Solver (Self-Hosted)

**Repo:** `github.com/waguriagentic/captcha-solver`
**Install path:** `/root/captcha-solver/`
**Service:** `captcha-solver.service` (systemd, enabled, auto-restart)
**Port:** `8877`

**Supported types:** turnstile, recaptcha, hcaptcha, cloudflare, awswaf, botguard, datadome, perimeterx, akamai, aliyun

**Key dependencies:** cloakbrowser (anti-detect Playwright), fastapi, uvicorn, onnxruntime, opencv-python-headless

**Setup steps:**
1. Clone repo → `/root/captcha-solver/`
2. `python3 -m venv .venv && .venv/bin/pip install fastapi uvicorn pydantic pillow onnxruntime opencv-python-headless numpy cloakbrowser`
3. `.venv/bin/python -m playwright install chromium`
4. Create `common/apikey.txt` (Mistral API keys, one per line — needed for image captcha solving)
5. Create systemd service running under `xvfb-run`
6. Test: `curl http://127.0.0.1:8877/health`

**API usage:**
```bash
curl -X POST http://localhost:8877/solve \
  -H 'Content-Type: application/json' \
  -d '{"type":"turnstile","sitekey":"0x4AAA...","url":"https://target.com"}'
```

**Cloudflare solver specifics:**
- Solves Managed Challenge (click Turnstile checkbox) and JS Challenge (auto-resolve)
- Returns `cf_clearance` cookie + `user_agent` + full cookie jar
- `cf_clearance` is bound to IP + JA3/TLS + User-Agent — replay must match all three
- `post_fetch` runs API calls from same browser session after solving
- POST requests to different endpoints on same domain MAY get re-challenged even with valid cf_clearance

## VPNX (Self-Hosted VPN Proxy)

**Repo:** `github.com/waguriagentic/vpnx`
**Install path:** `/root/vpnx/`
**Docker image:** `vpnx:local` (built from source)
**Container name:** `vpnx`

**Ports:** SOCKS5 `:1080`, HTTP `:8080`, API `:8000`
**API token:** `golem-vpnx-2026`

**Setup:**
1. Install Docker, start service
2. Build: `cd /root/vpnx && docker build -t vpnx:local .`
3. Run: `docker run -d --name vpnx --cap-add=NET_ADMIN --device=/dev/net/tun -p 1080:1080 -p 8080:8080 -p 8000:8000 -e API_TOKEN=<token> vpnx:local`

**API:**
- `GET /health` — status
- `POST /connect?country=XX` — connect to VPN
- `POST /rotate?country=XX` — rotate server
- `POST /disconnect` — disconnect
- `GET /locations` — list servers

**Limitations:**
- Uses free VPN Gate servers (datacenter IPs) — blocked by aggressive Cloudflare
- NOT suitable for bypassing Cloudflare bot protection
- Good for IP rotation, geo-testing, basic scraping

## Residential Proxies

**Asocks proxy format:**
```
socks5://username:password@ip:port
```

**Key insight:** Residential proxies help with IP reputation but Cloudflare also checks TLS fingerprint (JA3). `curl` has a different JA3 than browsers → still blocked. Need browser-based TLS (CloakBrowser, curl-cffi with `impersonate="chrome131"`).

## Cloudflare Bypass Patterns

**What works:**
- CloakBrowser (anti-detect Chromium) + headed mode under Xvfb
- captcha-solver service with `_click_turnstile_checkbox` for Managed Challenge
- Residential proxy improves success rate

**What does NOT work:**
- curl / requests / urllib — wrong TLS fingerprint, always blocked
- curl-cffi with browser impersonation — still blocked (no JS execution for challenge)
- VPN Gate free servers — datacenter IPs, blocked
- Replaying cf_clearance cookie via curl — JA3 mismatch
- POST requests via post_fetch to different endpoints — may get re-challenged per-endpoint

**Pattern:** Solve CF on page A → post_fetch to page B on same domain → 403. The cf_clearance is sometimes scoped per-URL-path, not just per-domain.

## 2captcha API (Cloud Service)

**Endpoint:** `https://2captcha.com/`
**API key used:** `8b4a438be2901da801b9fc1b37fff41a`

**Async flow:**
1. `POST /in.php` with task data → returns task ID
2. Poll `GET /res.php?key=...&action=get&id=...` → `CAPCHA_NOT_READY` then solution
3. `GET /res.php?key=...&action=getbalance` → balance amount

**Task types:**
- `method=userrecaptcha` — reCAPTCHA v2/v3/Enterprise
- `method=base64` — Image captcha (base64 encoded image)

**reCAPTCHA Enterprise:**
```python
requests.post("https://2captcha.com/in.php", data={
    "key": API_KEY, "method": "userrecaptcha",
    "googlekey": SITEKEY, "pageurl": PAGE_URL,
    "enterprise": "1", "json": "1"
})
```

**Image captcha:**
```python
requests.post("https://2captcha.com/in.php", data={
    "key": API_KEY, "method": "base64",
    "body": base64.b64encode(image_bytes).decode(), "json": "1"
})
```

**Polling pattern:**
```python
for i in range(30):
    time.sleep(5)  # reCAPTCHA takes 60-120s
    r = requests.get(f"https://2captcha.com/res.php?key={API_KEY}&action=get&id={task_id}&json=1")
    if r.json()["status"] == 1: return r.json()["request"]  # solution
    if r.json()["request"] != "CAPCHA_NOT_READY": return None  # error
```

**Common pitfalls:**
- reCAPTCHA Enterprise takes 60-120s to solve — be patient
- Image captcha codes expire quickly — use immediately after solving
- Use `enterprise=1` for Enterprise reCAPTCHA keys
- Response format: `{status: 1, request: "TOKEN_STRING"}` for success

### Two-Phase Captcha Flow (Xiaomi Pattern)

Some APIs require a TWO-PHASE captcha approach:
1. Send request WITHOUT captcha → server returns captcha URL in error response
2. GET the captcha image from that URL (same session cookies!)
3. Solve via 2captcha
4. Resend request WITH captcha code

This is different from the typical "solve captcha first, then submit" pattern.
The server needs the first request to determine WHICH captcha to show.

**File upload method** works better than base64 for some captcha types:
```python
requests.post("https://2captcha.com/in.php",
    files={"file": ("captcha.jpg", image_bytes, "image/jpeg")},
    data={"key": API_KEY, "json": "1"})
```

## Xiaomi Account Crypto System (Reference)

See `references/xiaomi-crypto.md` for full analysis. Key points:
- AES-CBC encryption (IV: `0102030405060708`, random 16-char key)
- RSA public keys for EUI and param encryption (1024-bit SPKI)
- GeeTest + reCAPTCHA Enterprise captcha
- Browser fingerprint collection
- **Email registration** uses `sendEmailRegTicket` with `email`/`password` fields (AES-encrypted)
- **Login** uses `serviceLoginAuth2` with `user`/`hash` fields (MD5 password)
- See `web-api-reverse-engineering` skill for full Xiaomi API details
