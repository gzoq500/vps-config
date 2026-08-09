#!/usr/bin/env python3
"""
MiMo Referral — nodriver (undetected Chrome via CDP)
navigator.webdriver = False, real Chrome fingerprint

Flow: API auth → nodriver browser → Terms → Enter Invite Code → Redeem
"""
import asyncio, json, os, re, sys, time, requests, base64, random
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad
from urllib.parse import urlencode

AES_IV = b"0102030405060708"
CS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*"
RSA_KEY_B64 = "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCYEVrK/4Mahiv0pUJgTybx4J9P5dUT/Y0PuwMbk+gMU+jrZnBiXGv6/hCH1avIhoBcE535F8nJQQN3UavZdFkYidsoXuEnat3+eVTp3FslyhRwIBDF09v4vDhRtxFOT+R7uH7h/mzmyA2/+lfIMWGIrffXprYizbV76+YQKhoqFQIDAQAB"
XI = "https://global.account.xiaomi.com"
MIMO = "https://platform.xiaomimimo.com"
REFERRAL = "QB3238"
STATUS_FILE = "/tmp/mimo_status.txt"

def status(s):
    with open(STATUS_FILE, "w") as f: f.write(s)
    print(s, flush=True)

def mk_eui(email, password):
    rk = ''.join(random.choice(CS) for _ in range(16))
    ct = PKCS1_v1_5.new(RSA.import_key(base64.b64decode(RSA_KEY_B64))).encrypt(base64.b64encode(rk.encode()).decode().encode())
    rsa_b64 = base64.b64encode(ct).decode()
    kb = rk.encode()
    enc_e = base64.b64encode(AES.new(kb, AES.MODE_CBC, AES_IV).encrypt(pad(email.encode(), AES.block_size))).decode()
    enc_p = base64.b64encode(AES.new(kb, AES.MODE_CBC, AES_IV).encrypt(pad(password.encode(), AES.block_size))).decode()
    return f"{rsa_b64}.{base64.b64encode(b'email,password').decode()}", enc_e, enc_p

def api(s, ep, email, pw, extra=None):
    eui, enc_e, enc_p = mk_eui(email, pw)
    data = {"email": enc_e, "password": enc_p, "region": "ID", "sid": "api-platform"}
    if extra: data.update(extra)
    r = s.post(f"{XI}/pass/{ep}", data=urlencode(data), headers={"EUI": eui, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "X-Requested-With": "XMLHttpRequest"})
    return json.loads(r.text.replace("&&&START&&&", "").replace("@json:", ""))

async def main():
    EMAIL = sys.argv[1] if len(sys.argv) > 1 else input("Email: ").strip()
    PASSWORD = sys.argv[2] if len(sys.argv) > 2 else input("Password: ").strip()

    for f in ["/tmp/mimo_code.txt", STATUS_FILE]:
        if os.path.exists(f): os.remove(f)

    # Step 1: API flow
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"})
    s.get(f"{XI}/fe/service/register/email?_locale=en_US&region=ID&sid=api-platform")

    status("READY")
    print("READY", flush=True)
    code = None
    for _ in range(300):
        if os.path.exists("/tmp/mimo_code.txt"):
            with open("/tmp/mimo_code.txt") as f: code = f.read().strip()
            if code: os.remove("/tmp/mimo_code.txt"); break
        time.sleep(0.5)
    if not code: status("TIMEOUT"); return

    print(f"CODE:{code}", flush=True)
    d = api(s, "verifyEmailRegTicket", EMAIL, PASSWORD, {"ticket": code, "icode": code})
    print(f"  verify: code={d.get('code')} uid={d.get('userId','')}", flush=True)
    if d.get("code") != 0: status("VERIFY_FAIL"); return

    r2 = s.get(d.get("user_synced_url", ""), allow_redirects=True)
    pt = s.cookies.get("passToken", domain=".account.xiaomi.com")
    cuid = s.cookies.get("cUserId", domain=".account.xiaomi.com")
    uid = d.get("userId", "")
    print(f"  pt: {pt[:40] if pt else 'NONE'}", flush=True)
    if not pt: status("NO_PT"); return

    r3 = s.post(f"{MIMO}/api/v1/invitation/bind", json={"code": REFERRAL}, headers={"Content-Type": "application/json"})
    lu = r3.json().get("loginUrl", "")
    svc = None
    url = lu
    for _ in range(10):
        if not url: break
        r = s.get(url, allow_redirects=False)
        loc = r.headers.get("Location", "")
        sc = r.headers.get("Set-Cookie", "")
        if "serviceToken" in sc:
            m = re.search(r'api-platform_serviceToken="?([^";]+)', sc)
            if m: svc = m.group(1)
        if loc and "invitation/bind" in loc: break
        url = loc
    if not svc: status("NO_SVC"); print("NO_SVC"); return
    print(f"  svc: {svc[:40]}...", flush=True)

    # Step 2: nodriver (undetected Chrome)
    status("BROWSER")
    import nodriver as uc

    browser = await uc.start(
        browser_args=["--no-sandbox", "--disable-dev-shm-usage", "--window-size=1920,1080"],
    )

    page = await browser.get("about:blank")

    # Set cookies via CDP
    for cookie in [
        {"name": "api-platform_serviceToken", "value": svc, "domain": "platform.xiaomimimo.com", "path": "/"},
        {"name": "passToken", "value": pt, "domain": ".account.xiaomi.com", "path": "/"},
        {"name": "cUserId", "value": cuid, "domain": ".account.xiaomi.com", "path": "/"},
        {"name": "userId", "value": uid, "domain": ".account.xiaomi.com", "path": "/"},
    ]:
        await page.send(uc.cdp.network.set_cookie(**cookie))

    # Navigate (use evaluate for URL since page.url is empty in nodriver)
    await asyncio.sleep(random.uniform(1, 3))
    page = await browser.get(f"{MIMO}/console/balance")
    # Wait for page to fully load
    for _ in range(30):
        await asyncio.sleep(1)
        try:
            ready = await page.evaluate("document.readyState")
            if ready == "complete":
                break
        except:
            pass
    await asyncio.sleep(random.uniform(5, 8))

    # Get URL via JS (page.url is EMPTY in nodriver!)
    url = await page.evaluate("window.location.href")
    print(f"  URL: {url[:120]}", flush=True)
    if "login" in url.lower():
        status("LOGIN_FAIL"); browser.stop(); return  # NOT await browser.stop()
    print("  LOGGED_IN!", flush=True)

    # Accept Terms
    await asyncio.sleep(random.uniform(0.5, 1.5))
    await page.evaluate('() => { const cb = document.querySelector("input[type=checkbox]"); if (cb && !cb.checked) cb.click(); }')
    await asyncio.sleep(random.uniform(0.3, 0.8))
    await page.evaluate('() => { const btns = document.querySelectorAll("button"); for (const b of btns) { if (b.innerText.trim().toLowerCase() === "confirm") { b.click(); break; } } }')
    await asyncio.sleep(random.uniform(4, 6))
    await page.evaluate('() => { const btns = document.querySelectorAll("button"); for (const b of btns) { if (b.innerText.toLowerCase().includes("accept all")) { b.click(); break; } } }')
    await asyncio.sleep(random.uniform(4, 6))
    print("  TERMS_OK", flush=True)

    # Click Enter Invite Code (JS evaluation more reliable than page.find())
    await asyncio.sleep(random.uniform(1, 2))
    try:
        click_result = await page.evaluate('''() => {
            const all = document.querySelectorAll('*');
            for (const el of all) {
                if (el.offsetParent !== null && el.innerText && el.innerText.includes('Enter Invite Code')) {
                    el.click();
                    return 'clicked: ' + el.tagName + ' ' + el.innerText.substring(0, 50);
                }
            }
            return 'not_found';
        }''')
        print(f"  CLICKED_INVITE: {click_result}", flush=True)
    except Exception as e:
        print(f"  click_failed: {e}", flush=True)
    await asyncio.sleep(random.uniform(2, 4))

    # Find inputs
    input_count = await page.evaluate('Array.from(document.querySelectorAll("input[type=text]")).filter(el => el.offsetParent !== null).length')
    print(f"  INPUTS: {input_count}", flush=True)

    if input_count >= 6:
        await page.evaluate('document.querySelectorAll("input[type=text]")[0].click()')
        await asyncio.sleep(random.uniform(0.3, 0.8))

        # Type via CDP Input events
        for ch in REFERRAL:
            code_str = f"Key{ch}" if ch.isalpha() else f"Digit{ch}" if ch.isdigit() else ch
            try:
                await page.send(uc.cdp.input_.dispatch_key_event(type_="keyDown", text=ch, key=ch, code=code_str, windows_virtual_key_code=ord(ch)))
                await page.send(uc.cdp.input_.dispatch_key_event(type_="keyUp", key=ch, code=code_str, windows_virtual_key_code=ord(ch)))
            except: pass
            await asyncio.sleep(random.uniform(0.08, 0.25))
        print(f"  TYPED: {REFERRAL}", flush=True)

        # Check checkbox
        await asyncio.sleep(random.uniform(0.5, 1))
        await page.evaluate('''() => {
            const inputs = Array.from(document.querySelectorAll('input[type="text"]')).filter(el => el.offsetParent !== null);
            if (inputs.length < 6) return;
            const ir = inputs[0].getBoundingClientRect();
            for (const cb of document.querySelectorAll('input[type=checkbox]')) {
                const cr = cb.getBoundingClientRect();
                if (Math.abs(cr.y - ir.y) < 100 && !cb.checked) { cb.click(); break; }
            }
        }''')
        await asyncio.sleep(random.uniform(1, 2))

        # Click Redeem (JS evaluation more reliable than page.find())
        try:
            redeem_result = await page.evaluate('''() => {
                const btns = document.querySelectorAll('button');
                for (const b of btns) {
                    if (b.offsetParent !== null && b.innerText && b.innerText.toLowerCase().includes('redeem')) {
                        b.click();
                        return 'clicked: ' + b.innerText.substring(0, 50);
                    }
                }
                return 'not_found';
            }''')
            print(f"  REDEEM: {redeem_result}", flush=True)
        except Exception as e:
            print(f"  redeem_fail: {e}", flush=True)

        await asyncio.sleep(random.uniform(8, 12))

        # Check result
        body = await page.evaluate("document.body.innerText.substring(0, 500)")
        print(f"  RESULT: {body[:300]}", flush=True)

        if "success" in body.lower() or "applied" in body.lower():
            status("SUCCESS")
            print(f"\nREFERRAL {REFERRAL} APPLIED!", flush=True)
            browser.stop(); return  # NOT await browser.stop()

    status("SUBMITTED")
    print("SUBMITTED", flush=True)
    try: browser.stop()  # NOT await — browser.stop() is NOT async in nodriver
    except: pass

asyncio.run(main())
