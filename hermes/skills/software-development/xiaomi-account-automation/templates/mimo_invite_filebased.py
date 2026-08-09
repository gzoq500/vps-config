#!/usr/bin/env python3
"""
Playwright login + verify + invite code entry (file-based communication).
For background process use — communicates via files instead of stdin.

Usage:
  1. Run in background: xvfb-run -a python3 mimo_invite_filebased.py
  2. Wait for /tmp/mimo_status.txt to contain "NEED_CODE"
  3. Write verification code to /tmp/mimo_code.txt
  4. Check /tmp/mimo_status.txt for result

Modify EMAIL, PASSWORD, REFERRAL constants before use.
"""
import asyncio, json, sys, os, time
sys.path.insert(0, '/root/captcha-solver')
from cloakbrowser import launch_async

EMAIL = 'user@example.com'
PASSWORD = 'password'
REFERRAL = 'QB3238'
STATUS_FILE = '/tmp/mimo_status.txt'
CODE_FILE = '/tmp/mimo_code.txt'

async def safe_eval(page, js, default=None):
    try: return await page.evaluate(js)
    except: return default

async def main():
    for f in [STATUS_FILE, CODE_FILE]:
        if os.path.exists(f): os.remove(f)

    async with await launch_async(headless=False) as browser:
        page = await browser.new_page()
        write_status = lambda m: open(STATUS_FILE, 'w').write(m) or print(m, flush=True)

        # Login
        write_status('LOGIN')
        await page.goto('https://platform.xiaomimimo.com/console/balance', timeout=60000)
        await page.wait_for_timeout(8000)

        for i in range(20):
            has = await safe_eval(page, '() => !!document.querySelector(\'input[name="account"]\')', False)
            if has: break
            await page.wait_for_timeout(1000)

        await page.fill('input[name="account"]', EMAIL, force=True)
        await page.fill('input[type="password"]', PASSWORD, force=True)
        await safe_eval(page, '() => { const cb = document.querySelector("input[type=checkbox]"); if (cb) cb.click(); }')
        await page.wait_for_timeout(1000)
        await page.click('button:has-text("Sign in")', force=True)
        await page.wait_for_timeout(12000)

        # Verify if needed
        if 'verify' in page.url.lower():
            write_status('NEED_CODE')
            await safe_eval(page, '''() => { const btns = document.querySelectorAll("button"); for (const b of btns) { if (b.innerText.includes("Send")) { b.click(); break; } } }''')
            await page.wait_for_timeout(5000)

            # Wait for input
            for i in range(15):
                has = await safe_eval(page, '() => !!document.querySelector(\'input[name="ticket"]\')', False)
                if has: break
                await page.wait_for_timeout(1000)

            # Wait for code from file
            code = None
            for _ in range(180):
                if os.path.exists(CODE_FILE):
                    with open(CODE_FILE) as f: code = f.read().strip()
                    if code: os.remove(CODE_FILE); break
                time.sleep(1)
            if not code: write_status('TIMEOUT'); return

            for i in range(5):
                try: await page.fill('input[name="ticket"]', code, force=True); break
                except: await page.wait_for_timeout(2000)
            await safe_eval(page, '''() => { const btns = document.querySelectorAll("button"); for (const b of btns) { if (b.innerText.includes("Submit")) { b.click(); break; } } }''')
            await page.wait_for_timeout(10000)

            if 'verify' in page.url.lower():
                text = await safe_eval(page, '() => document.body.innerText.substring(0, 200)', '')
                if 'error' in text.lower():
                    write_status(f'VERIFY_FAILED:{text[:100]}'); return
            write_status('VERIFIED')

        # Navigate to invite page
        write_status('INVITE')
        await page.goto('https://platform.xiaomimimo.com/console/invite', timeout=30000)
        await page.wait_for_timeout(8000)

        if 'login' in page.url.lower():
            write_status('LOGIN_FAILED'); return

        # Try API bind from browser context
        result = await safe_eval(page, f'''() => {{
            return fetch('/api/v1/invitation/bind', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{code: '{REFERRAL}'}}),
                credentials: 'include'
            }}).then(r => r.text()).catch(e => 'Error: ' + e.message);
        }}''', 'failed')
        write_status(f'DONE:{result[:500]}')
        await page.screenshot(path='/root/mimo_invite_result.png')

asyncio.run(main())
