# nodriver — Undetected Chrome Automation

## Why nodriver?

**BREAKTHROUGH (2026-07-19)**: User confirmed MiMo referral works fine when done manually from a real browser. Playwright is DETECTED — even with comprehensive stealth injection, MiMo's `api-platform_ph` fingerprint hash catches it.

nodriver uses Chrome DevTools Protocol directly (no chromedriver/Playwright). Result: `navigator.webdriver = False`.

## Install

```bash
pip install --index-url https://pypi.org/simple/ nodriver
# Requires real Google Chrome (not Chromium)
# Installed: Google Chrome 150 at /usr/bin/google-chrome
```

## Basic Usage

```python
import nodriver as uc

async def main():
    browser = await uc.start(
        browser_args=["--no-sandbox", "--disable-dev-shm-usage", "--window-size=1920,1080"],
    )
    page = await browser.get("https://example.com")
    await asyncio.sleep(5)
    
    # Verify stealth
    result = await page.evaluate("navigator.webdriver")  # Returns False!
    ua = await page.evaluate("navigator.userAgent")       # Real Chrome UA
    
    browser.stop()  # NOT async — do not await
```

## Setting Cookies (CDP)

```python
page = await browser.get("about:blank")
await page.send(uc.cdp.network.set_cookie(
    name="cookie_name",
    value="cookie_value",
    domain=".example.com",
    path="/",
))
```

## Typing (CDP Input Events)

```python
# Focus element
await page.evaluate('document.querySelector("input").click()')

# Type character by character (human-like)
for ch in "QB3238":
    await page.send(uc.cdp.input_.dispatch_key_event(
        type_="keyDown", text=ch, key=ch,
        code=f"Key{ch}" if ch.isalpha() else f"Digit{ch}" if ch.isdigit() else ch,
        windows_virtual_key_code=ord(ch),
    ))
    await page.send(uc.cdp.input_.dispatch_key_event(
        type_="keyUp", key=ch,
        code=f"Key{ch}" if ch.isalpha() else f"Digit{ch}" if ch.isdigit() else ch,
        windows_virtual_key_code=ord(ch),
    ))
    await asyncio.sleep(random.uniform(0.08, 0.25))
```

## Finding Elements

```python
el = await page.find("Button Text", best_match=True)
if el: await el.click()

# Prefer JS evaluation — more reliable than find()
await page.evaluate('document.querySelector("button").click()')
```

## Error Handling

The `page.evaluate()` return for `uc.cdp.input_.dispatch_key_event` may be None. Use try/except or check type before awaiting.

## MiMo Flow with nodriver

```python
# Step 1: API flow (register → verify → passToken → STS → serviceToken)
# ... (same as before, using requests)

# Step 2: nodriver browser
browser = await uc.start(browser_args=["--no-sandbox", "--window-size=1920,1080"])
page = await browser.get("about:blank")

# Set cookies
for cookie in [serviceToken, passToken, cUserId, userId]:
    await page.send(uc.cdp.network.set_cookie(**cookie))

# Navigate to console
page = await browser.get(f"{MIMO}/console/balance")
# MUST wait for readyState — page.url is often empty
for _ in range(30):
    await asyncio.sleep(1)
    try:
        if await page.evaluate("document.readyState") == "complete":
            break
    except Exception:
        pass
await asyncio.sleep(random.uniform(5, 8))

url = await page.evaluate("window.location.href")  # NOT page.url
# dump body text before assuming console loaded
body = await page.evaluate("document.body && document.body.innerText ? document.body.innerText.substring(0,500) : ''")

# Accept Terms
await page.evaluate('() => { const cb = document.querySelector("input[type=checkbox]"); if (cb && !cb.checked) cb.click(); }')
await asyncio.sleep(0.5)
await page.evaluate('() => { const btns = document.querySelectorAll("button"); for (const b of btns) { if (b.innerText.trim().toLowerCase() === "confirm") { b.click(); break; } } }')
await asyncio.sleep(5)
await page.evaluate('() => { const btns = document.querySelectorAll("button"); for (const b of btns) { if (b.innerText.toLowerCase().includes("accept all")) { b.click(); break; } } }')
await asyncio.sleep(5)

# Click Enter Invite Code via JS (find() is flaky)
await page.evaluate('''() => {
  for (const el of document.querySelectorAll('*')) {
    if (el.offsetParent !== null && el.innerText && el.innerText.includes('Enter Invite Code')) {
      el.click(); return 'clicked';
    }
  }
  return 'not_found';
}''')
await asyncio.sleep(3)

# Count OTP inputs — null-check evaluate results
input_count = await page.evaluate('Array.from(document.querySelectorAll("input[type=text]")).filter(el => el.offsetParent !== null).length')
all_inputs = await page.evaluate('''() => Array.from(document.querySelectorAll('input')).map(el => ({
  type: el.type, visible: el.offsetParent !== null
}))''')
# all_inputs may be None if page not ready — never do all_inputs[:10] without check
if all_inputs is None:
    all_inputs = []

if input_count and input_count >= 6:
    await page.evaluate('document.querySelectorAll("input[type=text]")[0].click()')
    await asyncio.sleep(0.5)
    for ch in "QB3238":
        await page.send(uc.cdp.input_.dispatch_key_event(type_="keyDown", text=ch, key=ch,
            code=f"Key{ch}" if ch.isalpha() else f"Digit{ch}" if ch.isdigit() else ch,
            windows_virtual_key_code=ord(ch)))
        await page.send(uc.cdp.input_.dispatch_key_event(type_="keyUp", key=ch,
            code=f"Key{ch}" if ch.isalpha() else f"Digit{ch}" if ch.isdigit() else ch,
            windows_virtual_key_code=ord(ch)))
        await asyncio.sleep(random.uniform(0.08, 0.25))

    await page.evaluate('''() => {
        const inputs = Array.from(document.querySelectorAll('input[type="text"]')).filter(el => el.offsetParent !== null);
        if (inputs.length < 6) return;
        const ir = inputs[0].getBoundingClientRect();
        for (const cb of document.querySelectorAll('input[type=checkbox]')) {
            const cr = cb.getBoundingClientRect();
            if (Math.abs(cr.y - ir.y) < 100 && !cb.checked) { cb.click(); break; }
        }
    }''')
    await asyncio.sleep(1)

    await page.evaluate('''() => {
      for (const b of document.querySelectorAll('button')) {
        if ((b.innerText||'').includes('Redeem')) { b.click(); return 'clicked'; }
      }
      return 'not_found';
    }''')
    await asyncio.sleep(10)
```

## Status vs MiMo 400909 (2026-07-22)

- `navigator.webdriver=False` confirmed on bot.sannysoft-style checks
- **Not yet proven** that MiMo `api-platform_ph` accepts nodriver
- Observed blockers before Redeem: `INPUTS:0`, empty URL, Terms/sidebar not rendered, evaluate returning `None`
- Until 6 OTP fields are visible and Redeem fires, do not claim 400909 fixed
- Fallback: semi-manual (API tokens + user redeems in real browser)

## Pitfalls

1. **page.evaluate() returns None for CDP send**: Don't assume return values.
2. **asyncio.sleep, not time.sleep**: nodriver is fully async.
3. **Xvfb required on headless servers**: `xvfb-run -a python3 script.py`.
4. **Chrome 150 required**: real Chrome, not Playwright Chromium only.
5. **find() with best_match=True**: flaky; prefer evaluate DOM queries.
6. **Cookie domain matters**: `platform.xiaomimimo.com` for serviceToken, `.account.xiaomi.com` for passToken/cUserId/userId.
7. **`page.url` is EMPTY**: always `window.location.href`.
8. **`browser.stop()` is NOT async**.
9. **Cookie setting**: CDP set_cookie before navigate.
10. **Page load wait**: readyState loop + body text dump.
11. **Click via JS more reliable** than find().
12. **Multiple browser.get()**: use latest page reference.
13. **Cleanup error** if event loop already closed — try/except stop.
14. **INPUTS:0 after LOGGED_IN claim**: often Terms not accepted or SPA still on shell — dump body text and check for "Enter Invite Code" before typing.
15. **null-check evaluate arrays**: `all_inputs[:10]` crashes if None.

## DrissionPage (Alternative)

Also installed but has WebSocket handshake issues (404 status). Use nodriver instead.

## Test Results (2026-07-19)

```
navigator.webdriver: False  ✅ (nodriver)
navigator.webdriver: true   ❌ (Playwright without stealth)
navigator.webdriver: undefined ❌ (Playwright with stealth - still detected via other signals)
UA: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36
```

## Script

`/root/mimo_nodriver.py` — Complete flow: API auth + nodriver browser + Terms + Enter Code + Redeem.
