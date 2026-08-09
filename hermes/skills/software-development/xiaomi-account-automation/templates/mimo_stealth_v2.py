#!/usr/bin/env python3
"""
MiMo Stealth v2 — Full anti-bot fingerprint bypass with human-like behavior.
Usage: python3 mimo_stealth_v2.py "email@x.com" "password123"
Waits for verification code via /tmp/mimo_code.txt, writes status to /tmp/mimo_status.txt.
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
STEALTH_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# JS as raw string (NOT f-string) to avoid escaping issues
STEALTH_JS = r"""
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
Object.defineProperty(navigator, 'vendor', {get: () => 'Google Inc.'});
Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 0});

window.chrome = {
    runtime: {connect: function(){}, sendMessage: function(){}, id: undefined},
    loadTimes: function() { return {commitLoadTime: Date.now()/1000, finishDocumentLoadTime: Date.now()/1000+0.1, finishLoadTime: Date.now()/1000+0.2, firstPaintTime: Date.now()/1000+0.05, navigationType: 'Other', requestTime: Date.now()/1000-0.3, wasFetchedViaSpdy: true}; },
    csi: function() { return {onloadT: Date.now(), pageT: Date.now() - performance.timing.navigationStart}; },
    app: {isInstalled: false}
};

const getParam = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(p) {
    if (p === 37445) return 'Google Inc. (Intel)';
    if (p === 37446) return 'ANGLE (Intel, Intel(R) UHD Graphics 630, OpenGL 4.5)';
    return getParam.apply(this, arguments);
};
const getParam2 = WebGL2RenderingContext.prototype.getParameter;
WebGL2RenderingContext.prototype.getParameter = function(p) {
    if (p === 37445) return 'Google Inc. (Intel)';
    if (p === 37446) return 'ANGLE (Intel, Intel(R) UHD Graphics 630, OpenGL 4.5)';
    return getParam2.apply(this, arguments);
};

const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(type) {
    if (type === 'image/png' || type === 'image/webp') {
        const ctx = this.getContext('2d');
        if (ctx) {
            const d = ctx.getImageData(0, 0, this.width, this.height);
            for (let i = 0; i < d.data.length; i += 4) d.data[i] = d.data[i] ^ (d.data[i] & 1);
            ctx.putImageData(d, 0, 0);
        }
    }
    return origToDataURL.apply(this, arguments);
};

Object.defineProperty(screen, 'width', {get: () => 1920});
Object.defineProperty(screen, 'height', {get: () => 1080});
Object.defineProperty(screen, 'availWidth', {get: () => 1920});
Object.defineProperty(screen, 'availHeight', {get: () => 1040});
Object.defineProperty(screen, 'colorDepth', {get: () => 24});
Object.defineProperty(window, 'devicePixelRatio', {get: () => 1});
Object.defineProperty(window, 'outerWidth', {get: () => 1920});
Object.defineProperty(window, 'outerHeight', {get: () => 1000});
Object.defineProperty(window, 'innerWidth', {get: () => 1904});
Object.defineProperty(window, 'innerHeight', {get: () => 920});

const origQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (params) => (
    params.name === 'notifications' ? Promise.resolve({state: Notification.permission}) : origQuery(params)
);

Object.defineProperty(navigator, 'plugins', {get: () => {
    const p = [{name:'Chrome PDF Plugin',filename:'internal-pdf-viewer'},{name:'Chrome PDF Viewer',filename:'mhjfbmdgcfjbbpaeojofohoefgiehjai'},{name:'Native Client',filename:'internal-nacl-plugin'}];
    p.length = 3; return p;
}});

if (navigator.connection) {
    Object.defineProperty(navigator.connection, 'effectiveType', {get: () => '4g'});
    Object.defineProperty(navigator.connection, 'downlink', {get: () => 10});
    Object.defineProperty(navigator.connection, 'rtt', {get: () => 50});
}

if (navigator.getBattery) navigator.getBattery = () => Promise.resolve({charging:true,level:0.95,addEventListener:function(){},removeEventListener:function(){}});

delete navigator.__proto__.webdriver;
delete navigator.webdriver;

const nativeToString = Function.prototype.toString;
Function.prototype.toString = function() {
    if (this === Function.prototype.toString) return 'function toString() { [native code] }';
    return nativeToString.call(this);
};
"""


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

async def human_delay(lo=100, hi=500):
    await asyncio.sleep(random.randint(lo, hi) / 1000)

async def human_type(page, text, lo=80, hi=250):
    for ch in text:
        await page.keyboard.press(ch)
        await human_delay(lo, hi)

async def main():
    EMAIL = sys.argv[1] if len(sys.argv) > 1 else input("Email: ").strip()
    PASSWORD = sys.argv[2] if len(sys.argv) > 2 else input("Password: ").strip()
    for f in ["/tmp/mimo_code.txt", STATUS_FILE]:
        if os.path.exists(f): os.remove(f)

    s = requests.Session()
    s.headers.update({"User-Agent": STEALTH_UA})
    s.get(f"{XI}/fe/service/register/email?_locale=en_US&region=ID&sid=api-platform")
    status("READY")
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

    status("BROWSER")
    sys.path.insert(0, "/root/captcha-solver")
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=[
            "--no-sandbox", "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials", "--disable-infobars",
            "--window-size=1920,1080", "--disable-dev-shm-usage",
            "--no-first-run", "--no-default-browser-check", "--disable-extensions",
        ])
        ctx = await browser.new_context(
            viewport={"width": 1920, "height": 1080}, user_agent=STEALTH_UA,
            locale="en-US", timezone_id="America/New_York", color_scheme="light",
            has_touch=False, is_mobile=False,
        )
        await ctx.add_cookies([
            {"name": "api-platform_serviceToken", "value": svc, "domain": "platform.xiaomimimo.com", "path": "/"},
            {"name": "passToken", "value": pt, "domain": ".account.xiaomi.com", "path": "/"},
            {"name": "cUserId", "value": cuid, "domain": ".account.xiaomi.com", "path": "/"},
            {"name": "userId", "value": uid, "domain": ".account.xiaomi.com", "path": "/"},
        ])
        page = await ctx.new_page()
        await page.add_init_script(STEALTH_JS)
        await page.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9",
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        })

        bind_results = []
        async def on_resp(resp):
            if "invitation/bind" in resp.url:
                try: body = await resp.text(); bind_results.append({"status": resp.status, "body": body[:500]})
                except: bind_results.append({"status": resp.status})
        page.on("response", on_resp)

        await human_delay(1000, 3000)
        await page.goto(f"{MIMO}/console/balance", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=30000)
        await page.wait_for_timeout(random.randint(8000, 12000))

        async def safe(js, d=None):
            try: return await page.evaluate(js)
            except: return d

        url = page.url
        print(f"  URL: {url[:120]}", flush=True)
        if "login" in url.lower():
            status("LOGIN_FAIL"); await browser.close(); return
        print("  LOGGED_IN!", flush=True)

        # Accept Terms
        await human_delay(500, 1500)
        await safe('() => { const cb = document.querySelector("input[type=checkbox]"); if (cb && !cb.checked) cb.click(); }')
        await human_delay(300, 800)
        await safe('() => { const btns = document.querySelectorAll("button"); for (const b of btns) { if (b.innerText.trim().toLowerCase() === "confirm") { b.click(); break; } } }')
        await human_delay(4000, 6000)
        await safe('() => { const btns = document.querySelectorAll("button"); for (const b of btns) { if (b.innerText.toLowerCase().includes("accept all")) { b.click(); break; } } }')
        await human_delay(4000, 6000)
        print("  TERMS_OK", flush=True)

        # Click Enter Invite Code
        await human_delay(1000, 2000)
        try:
            await page.get_by_text("Enter Invite Code", exact=False).first.click(timeout=5000)
            print("  CLICKED_INVITE", flush=True)
        except Exception as e:
            print(f"  click_failed: {e}", flush=True)
        await human_delay(2000, 4000)

        ic = await safe('() => Array.from(document.querySelectorAll("input[type=text]")).filter(el => el.offsetParent !== null).length', 0)
        print(f"  INPUTS: {ic}", flush=True)

        if ic >= 6:
            await page.locator("input[type=text]").first.click(force=True)
            await human_delay(300, 800)
            await human_type(page, REFERRAL, 80, 250)
            print(f"  TYPED: {REFERRAL}", flush=True)

            await human_delay(500, 1000)
            await safe('''() => {
                const inputs = Array.from(document.querySelectorAll('input[type="text"]')).filter(el => el.offsetParent !== null);
                if (inputs.length < 6) return;
                const ir = inputs[0].getBoundingClientRect();
                for (const cb of document.querySelectorAll('input[type=checkbox]')) {
                    const cr = cb.getBoundingClientRect();
                    if (Math.abs(cr.y - ir.y) < 100 && !cb.checked) { cb.click(); break; }
                }
            }''')
            await human_delay(1000, 2000)

            try:
                await page.locator('button:has-text("Redeem")').first.click(timeout=5000)
                print("  REDEEM_CLICKED", flush=True)
            except Exception as e:
                print(f"  redeem_fail: {e}", flush=True)

            await page.wait_for_timeout(random.randint(8000, 12000))
            print(f"  BINDS: {len(bind_results)}", flush=True)
            for b in bind_results:
                print(f"    [{b['status']}]{b.get('body', '')[:300]}", flush=True)
                if b.get("status") == 200:
                    try:
                        j = json.loads(b.get("body", "{}"))
                        if j.get("code") == 0:
                            status("SUCCESS")
                            print(f"\nREFERRAL {REFERRAL} APPLIED!", flush=True)
                            await page.screenshot(path="/root/mimo_success.png")
                            await browser.close(); return
                    except: pass

        result = await safe("() => document.body.innerText.substring(0,500)", "")
        print(f"  RESULT: {result[:300]}", flush=True)
        await page.screenshot(path="/root/mimo_result.png")
        status("SUBMITTED"); print("SUBMITTED", flush=True); await browser.close()

asyncio.run(main())
