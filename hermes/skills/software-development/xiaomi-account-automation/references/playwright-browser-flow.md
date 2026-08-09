---
name: playwright-browser-flow
type: reference
---

# Playwright Browser Flow for Xiaomi/MiMo

## Setup

```bash
# Run Playwright with virtual display
xvfb-run -a /root/captcha-solver/.venv/bin/python3 script.py

# Or with DISPLAY variable
DISPLAY=:99 /root/captcha-solver/.venv/bin/python3 script.py
```

Use `cloakbrowser.launch_async(headless=False)` — headless may not render React components properly.

## Form Selectors

### Registration Page (`/fe/service/register/email`)
```
input[name="email"]          # Email field
input[name="password"]       # Password field  
input[name="repassword"]     # Confirm password
input[type="checkbox"]       # Terms checkbox (needs React fiber dispatch)
button:has-text("Next")      # Submit button
```

**Checkbox handling** (registration uses React):
```python
await page.evaluate("""() => {
    const cb = document.querySelector('input[type="checkbox"]');
    if (cb) {
        const key = Object.keys(cb).find(k => k.startsWith('__reactFiber$'));
        if (key) {
            let node = cb[key];
            while (node) {
                if (node.memoizedProps && node.memoizedProps.onChange) {
                    node.memoizedProps.onChange({target: {checked: true}});
                    break;
                }
                node = node.return;
            }
        }
        cb.checked = true;
    }
}""")
```

### Login Page (`/fe/service/login`)
```
input[name="account"]        # Email field (NOT "email"!)
input[type="password"]       # Password field
input[type="checkbox"]       # Terms checkbox (simple .click() works)
button:has-text("Sign in")   # Submit button
```

**Checkbox handling** (login page — simple):
```python
await page.evaluate('() => { const cb = document.querySelector("input[type=checkbox]"); if (cb) cb.click(); }')
```

### Verification Page (`/fe/service/identity/verifyEmail`)
```
button:has-text("Send")      # Click FIRST to reveal input
input[name="ticket"]         # Code input (appears AFTER Send click)
button:has-text("Submit")    # Submit code
```

**Critical:** The `input[name="ticket"]` does NOT exist until "Send" is clicked. Always click Send first, wait 2 seconds, then fill the input.

**HTML structure after Send click:**
```html
<input type="text" name="ticket" placeholder="Enter code" class="miui-input">
<button class="miui-btn miui-btn-primary">Submit</button>
<button disabled>Resend 43s</button>
```

**Send button click issue:** `page.click()` sometimes doesn't trigger React state. Use JS click instead:
```python
await page.evaluate('''() => {
    const btns = document.querySelectorAll("button");
    for (const b of btns) {
        if (b.innerText.includes("Send")) { b.click(); break; }
    }
}''')
```

## Captcha e Token Flow

The captcha system uses an `e` token from data collection:

1. Submit form → triggers POST to `/captcha/v2/data` with encrypted sensor data (RSA 2048-bit encrypted AES key in `s` field, AES-encrypted sensor data in `d` field)
2. Response: `{code: 0, data: {result: false, url: "https://...check.html?t=4&k=...&e=ENCODED_TOKEN..."}}`
3. Extract `e` from URL: `re.search(r'[?&]e=([^&]+)', data["data"]["url"])`
4. `e` is URL-encoded base64, ~364 chars
5. Use for image captcha: `GET /captcha/v2/image/register?e=ENCODED&e&k=8027422fb0eb42fbac1b521ec4a7961f`
6. Solve image, verify: `GET /captcha/v2/image/verify?code=CODE&token=TOKEN&e=ENCODED&e`
7. Response `data.token` = flag, use as `icode` in `sendEmailRegTicket`

**Key params:** `k=8027422fb0eb42fbac1b521ec4a7961f` (fixed for signup page)

**Note:** The `e` token expires quickly (~30 seconds). The simpler `/pass/getCode?icodeType=register` flow is more reliable.

**Note:** The `e` token CANNOT be generated from Python — the encryption format (RSA 2048-bit with specific padding) must match the browser's JS crypto exactly. Use Playwright to capture it via `page.on("response")`, then use it immediately in the same script.

## Network Interception

```python
# Capture captcha responses
async def on_response(response):
    if '/captcha/v2/data' in response.url:
        text = await response.text()
        data = json.loads(text)
        if data.get("data", {}).get("url"):
            e_match = re.search(r'[?&]e=([^&]+)', data["data"]["url"])
            if e_match:
                e_token = unquote(e_match.group(1))

page.on("response", on_response)
```

## MiMo API Calls from Browser

```python
# Authenticated API call (uses browser cookies)
result = await page.evaluate('''() => {
    return fetch('/api/v1/invitation/bind', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({code: 'REFERRAL_CODE'}),
        credentials: 'include'
    }).then(r => r.json());
}''')
```

## Pitfalls

1. `input[name="account"]` on login page, NOT `input[name="email"]`
2. Verification input appears only AFTER clicking "Send"
3. Checkbox on registration needs React fiber dispatch
4. **Browser sessions reset between turns**: Browserbase sessions die between assistant turns. Each `browser_navigate` starts fresh. Login + verification must happen in ONE continuous sequence.
5. Verification codes expire in ~60 seconds
6. `cloakbrowser` needs `xvfb-run -a` on headless Linux
7. React SPA may not render in headless mode — use `headless=False` with xvfb
8. **`safe_eval` pattern**: Wrap all `page.evaluate()` in try/except for pages with redirects:
   ```python
   async def safe_eval(page, js, default=None):
       try: return await page.evaluate(js)
       except: return default
   ```
9. **Invite page SPA issue**: `/console/invite` does NOT render referral input in headless Playwright. Page shows main MiMo content instead of invite section. Automated referral code entry via Playwright is unreliable. Manual browser interaction currently required.
10. **Playwright form load delay**: Registration page may take 10-20s to render. Use retry loop:
    ```python
    for i in range(20):
        has = await safe_eval(page, '() => !!document.querySelector("input[name=\\"account\\"]")', False)
        if has: break
        await page.wait_for_timeout(1000)
    ```
11. **Background process communication**: `input()` doesn't work in background processes. Use file-based approach:
    - Script writes status to `/tmp/mimo_status.txt`
    - Parent writes code to `/tmp/mimo_code.txt`
    - Script polls for code file with `time.sleep(1)` loop
12. **Password `$` in shell**: Dollar signs get interpreted as shell variables in `bash -c`. Use Python script files instead of inline commands.
13. **Verification code timing**: Codes expire in ~60 seconds. Minimize delay between Send click and code entry. The "Send" button triggers a new code each time — clicking Send again invalidates the previous code.
14. **Pre-write code pattern**: When user provides a code, write it to `/tmp/mimo_code.txt` BEFORE starting the Playwright script. Script polls for the file. Eliminates startup delay.
15. **Login verification page structure**: After login, URL may show `authStart` (identity verification) or `verifyEmail` (email verification). Both require different handling. `verifyEmail` has Send → input → Submit flow.
16. **Form submit button disabled**: The "Next" button on registration is disabled until all fields filled AND checkbox checked. Use `force=True` on clicks.
17. **e token capture**: The `e` token is obtained by intercepting `/captcha/v2/data` response via `page.on("response")`. Cannot generate from Python.
18. **`sendServiceLoginTicket` rate limit**: Returns `10001` (system error) when rate-limited. Persists across sessions, may last 24+ hours. Use `serviceLoginAuth2` with image captcha instead.
