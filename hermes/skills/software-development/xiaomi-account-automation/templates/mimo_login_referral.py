#!/usr/bin/env python3
"""
Login to MiMo + Enter referral code in one Playwright session.
Usage: python3 mimo_login_referral.py <VERIFY_CODE>
"""
import asyncio, json, sys
sys.path.insert(0, '/root/captcha-solver')
from cloakbrowser import launch_async

EMAIL = 'user@example.com'
PASSWORD = 'password'
REFERRAL = 'QB3238'
VERIFY_CODE = sys.argv[1] if len(sys.argv) > 1 else ''

async def main():
    async with await launch_async(headless=False) as browser:
        page = await browser.new_page()

        # Login
        await page.goto('https://platform.xiaomimimo.com/console/balance', wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(5000)
        await page.fill('input[name="account"]', EMAIL, force=True)
        await page.fill('input[type="password"]', PASSWORD, force=True)
        await page.evaluate('() => { const cb = document.querySelector("input[type=checkbox]"); if (cb) cb.click(); }')
        await page.wait_for_timeout(500)
        await page.click('button:has-text("Sign in")', force=True)
        await page.wait_for_timeout(10000)

        # Verify if needed
        if 'verify' in page.url.lower():
            if not VERIFY_CODE:
                print('NEED_VERIFY_CODE')
                return
            await page.click('button:has-text("Send")', timeout=5000)
            await page.wait_for_timeout(2000)
            await page.fill('input[name="ticket"]', VERIFY_CODE, force=True)
            await page.click('button:has-text("Submit")', force=True)
            await page.wait_for_timeout(10000)

        # Go to invite page
        await page.goto('https://platform.xiaomimimo.com/console/invite', wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(5000)

        if 'login' in page.url.lower():
            print('LOGIN_FAILED')
            return

        text = await page.evaluate('() => document.body.innerText.substring(0, 2000)')
        print(f'PAGE:{text[:1000]}')

        # Find and click Enter Code
        btns = await page.evaluate('''() => Array.from(document.querySelectorAll('button, a')).filter(el => {
            const t=(el.innerText||'').toLowerCase();
            return t.includes('enter') || t.includes('redeem') || t.includes('bind');
        }).map(el => ({text:el.innerText.substring(0,50).trim(), vis:el.offsetParent!==null}))''')
        for btn in btns:
            if btn.get('vis') and btn.get('text'):
                try:
                    await page.click(f'text="{btn["text"]}"', timeout=5000)
                    await page.wait_for_timeout(2000)
                except: pass

        # Enter referral code
        inputs = await page.evaluate('''() => Array.from(document.querySelectorAll('input')).filter(el =>
            el.offsetParent!==null && ['text','tel','number'].includes(el.type)
        ).map(el => ({type:el.type, name:el.name}))''')
        for inp in inputs:
            sel = f'input[name="{inp["name"]}"]' if inp.get('name') else f'input[type="{inp["type"]}"]'
            try:
                await page.fill(sel, REFERRAL, force=True)
                break
            except: pass

        # Submit
        try:
            await page.click('button:has-text("Redeem"), button:has-text("Bind"), button:has-text("Confirm"), button:has-text("Submit")', timeout=5000)
        except: pass

        await page.wait_for_timeout(5000)
        result = await page.evaluate('() => document.body.innerText.substring(0, 2000)')
        print(f'RESULT:{result[:1000]}')
        await page.screenshot(path='/tmp/mimo_referral_result.png')

asyncio.run(main())
