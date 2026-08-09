---
name: playwright-web-automation
description: >
  Automate web forms, login flows, and interactive pages with Playwright (Python).
  Study a page's structure via browser tools, then generate a reusable script.
  Covers: form filling, multi-step wizards, CAPTCHA/verification handling,
  error detection, screenshots, headless vs visible modes.
  Integrates with captcha-solver sidecar for automated CAPTCHA solving
  (Turnstile, reCAPTCHA, hCaptcha, Cloudflare, AWS WAF, etc.).
tags: [playwright, automation, web, forms, signup, scraping, browser]
triggers:
  - "automate a web form"
  - "script for signup/login/registration"
  - "fill out a form automatically"
  - "playwright script"
  - "web scraping with login"
  - "captcha solver setup"
  - "captcha-solver sidecar"
---

# Playwright Web Automation

Create Python scripts that automate interactive web pages — forms, signups, logins, multi-step wizards — using Playwright.

## When to use

- User asks to automate a signup, login, or form-filling flow
- User provides a URL and wants a reusable script
- Need to study a page first, then script it
- Need headless + visible (manual verification fallback) modes

## Prerequisites

```bash
pip install playwright
python -m playwright install chromium
python -m playwright install-deps chromium   # Linux only, installs system deps
```

## Workflow

### Step 1 — Study the page

Use `browser_navigate` + `browser_snapshot` to inspect the target page:
- Identify all form fields (textboxes, dropdowns, checkboxes, buttons)
- Note field types, placeholders, and selectors
- Check for hidden fields, CSRF tokens, dynamic content
- Identify potential blockers (CAPTCHA, email verification, rate limits)

### Step 2 — Create the script

Use the template pattern below. Key elements:

1. **URL construction** — preserve all query params exactly (they often contain auth tokens/callbacks)
2. **Form field selectors** — prefer `placeholder`, `type`, or `role` selectors over fragile CSS classes
3. **Error detection** — after submission, check for `.error`, `.err-tip`, `[class*="error"]` elements
4. **Verification handling** — if CAPTCHA/code appears, pause for manual input (visible mode) or exit gracefully (headless)
5. **Screenshot** — always save a screenshot after submission for debugging

### Step 3 — Test and iterate

Run with `--visible` first to verify the flow works, then switch to headless.

## Script Template

```python
#!/usr/bin/env python3
"""Web form automation script."""

import asyncio
import sys
import getpass
from playwright.async_api import async_playwright

TARGET_URL = "https://example.com/signup?param=value"


async def fill_form(email: str, password: str, headless: bool = False):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            locale="id-ID",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        print("[*] Opening page...")
        await page.goto(TARGET_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        # Fill fields — adjust selectors per page
        print(f"[*] Filling email: {email}")
        email_input = page.locator('input[type="text"], input[placeholder*="Email"]').first
        await email_input.click()
        await email_input.fill(email)

        print("[*] Filling password...")
        pw_inputs = page.locator('input[type="password"]')
        await pw_inputs.nth(0).fill(password)
        await pw_inputs.nth(1).fill(password)  # confirm field if present

        # Checkbox (agreement, terms, etc.)
        print("[*] Checking agreement...")
        checkbox = page.locator('input[type="checkbox"]')
        if await checkbox.count() > 0:
            await checkbox.first.check()
            await page.wait_for_timeout(500)

        # Submit
        print("[*] Clicking submit...")
        submit_btn = page.locator('button:has-text("Next"), button:has-text("Submit"), button:has-text("Sign up")')
        await submit_btn.first.click()
        await page.wait_for_timeout(3000)

        # Error detection
        error_el = page.locator('.error, .err-tip, [class*="error"]')
        if await error_el.count() > 0:
            err_text = await error_el.first.text_content()
            if err_text and err_text.strip():
                print(f"[!] Error: {err_text.strip()}")
                await browser.close()
                return False

        # Verification detection
        page_text = await page.inner_text("body")
        lower = page_text.lower()
        if any(kw in lower for kw in ["verify", "captcha", "code", "confirm"]):
            print("[!] Verification required (CAPTCHA/email code).")
            if not headless:
                print("[*] Waiting for manual verification (120s timeout)...")
                try:
                    await page.wait_for_url("**/success**", timeout=120000)
                    print("[✓] Success!")
                except Exception:
                    print("[!] Timeout. Check manually.")
            else:
                print("[!] Re-run with --visible for manual verification.")
                await browser.close()
                return False

        # Screenshot
        await page.screenshot(path="/root/signup_result.png", full_page=True)
        print("[*] Screenshot saved.")

        if not headless:
            print("[*] Browser open. Ctrl+C to exit.")
            await page.wait_for_timeout(30000)

        await browser.close()
        return True


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", "-e")
    parser.add_argument("--password", "-p")
    parser.add_argument("--visible", action="store_true")
    args = parser.parse_args()

    email = args.email or input("Email: ").strip()
    password = args.password or getpass.getpass("Password: ")

    await fill_form(email, password, headless=not args.visible)


if __name__ == "__main__":
    asyncio.run(main())
```

## Selector Strategy (priority order)

1. `placeholder` text — most stable: `input[placeholder*="Email"]`
2. `type` + position: `input[type="password"]` nth(0), nth(1)
3. `role` + label: `textbox "Email"`, `button "Next"`
4. `has-text`: `button:has-text("Sign up")`
5. CSS class/id — last resort, breaks on redesigns

## Captcha-Solver Sidecar Integration

For forms with CAPTCHA (Turnstile, reCAPTCHA, hCaptcha, Cloudflare, etc.), pair Playwright with a local captcha-solver HTTP sidecar. The solver runs on `http://127.0.0.1:8877` and accepts POST requests.

**Supported types:** turnstile, recaptcha, hcaptcha, cloudflare, awswaf, botguard, datadome, perimeterx, akamai, aliyun

**Setup pattern:**
```bash
git clone https://github.com/waguriagentic/captcha-solver.git /root/captcha-solver
cd /root/captcha-solver
python3 -m venv .venv
.venv/bin/pip install fastapi uvicorn pydantic pillow onnxruntime opencv-python-headless numpy cloakbrowser
.venv/bin/python -m playwright install chromium
apt-get install -y xvfb  # for headed mode on headless servers
```

**Run as systemd service:**
```ini
[Service]
WorkingDirectory=/root/captcha-solver
ExecStart=/usr/bin/xvfb-run /root/captcha-solver/.venv/bin/python server.py
Environment=TURNSTILE_HEADLESS=0
Environment=RECAPTCHA_HEADLESS=0
```

**Solve a captcha from script:**
```python
import requests
resp = requests.post("http://127.0.0.1:8877/solve", json={
    "type": "turnstile",
    "sitekey": "0x4AAAAAA...",
    "url": "https://target.com/login"
})
token = resp.json().get("token")
```

**Real-page mode** (navigate actual site + pre_actions + post_fetch):
```python
resp = requests.post("http://127.0.0.1:8877/solve", json={
    "type": "recaptcha", "version": "v2", "real_page": True,
    "url": "https://target.com/login",
    "pre_actions": [
        {"type": "fill", "selector": "input[type=email]", "value": "u@ex.com"},
        {"type": "click", "selector": "button[type=submit]"}
    ],
    "post_fetch": [
        {"url": "https://target.com/api/verify", "body": {"token": "__TOKEN__"}}
    ]
})
```

**Image captcha solving** (reCAPTCHA v2 checkbox, hCaptcha) requires Mistral API keys in `common/apikey.txt` (one per line, round-robin with auto-failover).

See `references/captcha-solver-setup.md` for full details.

## VPN Proxy (VPNX)

For IP rotation when scraping or bypassing rate limits, see `references/vpnx-vpn-proxy.md`. Docker-based VPN proxy using free VPN Gate servers — SOCKS5 + HTTP proxy with REST API for connect/rotate/disconnect.

## Third-Party Captcha Solver APIs

For services like Solverify, CapSolver, Anti-Captcha (remote HTTP API, not local sidecar), see `references/third-party-captcha-apis.md`. Same async pattern: createTask → poll getTaskResult. Note: many of these APIs are behind Cloudflare — datacenter IPs may be blocked.

## Pitfalls

- **CSRF tokens**: Some forms embed hidden tokens. If POST fails, check for `<input type="hidden">` fields and include them. Alternatively, intercept the form submission with `page.route()`.
- **Dynamic loading**: Use `wait_until="networkidle"` and explicit `wait_for_timeout()` after navigation. Some forms load fields via JS after page load.
- **CAPTCHA**: Integrate with captcha-solver sidecar (see above) or design script with `--visible` fallback for manual intervention.
- **Rate limiting**: Add delays between attempts. Don't loop without backoff.
- **Password rules**: Always validate password requirements before sending (length, character classes). Check the page's hint text.
- **Multi-step forms**: After clicking "Next", wait for the next step to load, then fill those fields. Chain steps sequentially.
- **Country/region selectors**: Often custom dropdowns (not native `<select>`). Use `set_value` or click-then-select pattern.
- **Playwright vs Selenium**: Playwright is preferred — faster, better async support, auto-wait built in, more reliable selectors.
- **pip detected as long-lived process**: The terminal tool may detect `pip install` or `source venv/bin/activate` as starting a long-lived server. Workaround: write install commands to a `.sh` script and run with `bash script.sh` in background, or call the venv binary directly (`/path/to/.venv/bin/pip install ...`).
- **CloakBrowser import**: Use `from cloakbrowser import launch_async` (returns Playwright Browser). Do NOT use `from cloakbrowser import CloakBrowser` — that class doesn't exist. Key params: `headless`, `humanize`, `proxy`, `geoip`, `stealth_args`.
- **Xvfb display conflicts**: If captcha-solver systemd service is already running on `:99`, other headful Playwright scripts need `xvfb-run -a` (auto-select display) or a different display number. `DISPLAY=:99` will fail with auth errors if the existing Xvfb owns it.
- **Cloudflare-protected APIs**: Many captcha solver services (solverify.net, etc.) put their API behind Cloudflare. Datacenter IPs are aggressively blocked — headless, headful, even CloakBrowser+humanize won't pass. Workarounds: (1) residential proxy, (2) run client from non-datacenter network, (3) use the local captcha-solver sidecar's own Cloudflare clearance to get `cf_clearance` cookie first.
- **Cloudflare re-challenge on API endpoints**: Even after solving CF on a page (e.g. solverify.net/), POST requests to API endpoints (e.g. /getBalance) trigger a NEW CF challenge. The `cf_clearance` cookie from page navigation does NOT carry over. The captcha-solver's `post_fetch` also hits this. This is fundamental CF behavior — not a solver bug. Workaround: residential proxy to avoid CF challenge entirely.
- **VPN Gate IPs are public/blocked**: Free VPN servers from VPN Gate are already flagged by Cloudflare and other anti-bot services. Using VPNX (socks5 proxy) doesn't help bypass CF on solver APIs. Only residential proxies work reliably from datacenter servers.
- **React checkbox click fails silently**: In React apps, `browser_click` on a checkbox element may NOT actually check it — React's synthetic event system doesn't always process DOM-level clicks. The checkbox appears clicked in the accessibility tree but React's internal state doesn't update. The form's submit button stays disabled because React thinks the checkbox is unchecked. Fix: use `browser_console` to access the React fiber and call the `onChange` handler directly:
  ```javascript
  const cb = document.querySelector('input[type="checkbox"]');
  const key = Object.keys(cb).find(k => k.startsWith('__reactFiber$'));
  let node = cb[key];
  while (node) {
    if (node.memoizedProps && node.memoizedProps.onChange) {
      node.memoizedProps.onChange({target: {checked: true}});
      break;
    }
    node = node.return;
  }
  cb.checked = true;
  ```
  After this, click the submit button via `browser_click`. This pattern is needed for Xiaomi account signup and similar React-based forms.
