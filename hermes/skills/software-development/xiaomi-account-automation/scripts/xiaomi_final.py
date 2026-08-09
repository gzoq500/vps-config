#!/usr/bin/env python3
"""
Xiaomi MiMo — Browserless Registration (PROVEN METHOD)
Uses /pass/getCode captcha flow with retry logic.

Usage:
  python3 xiaomi_final.py -e "email@domain.com"
  python3 xiaomi_final.py -e "email@domain.com" --verify 123456
"""
import argparse, base64, json, random, string, sys, time, requests, pickle
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad
from urllib.parse import urlencode, quote

TWOCAPTCHA_KEY = "YOUR_KEY"
AES_IV = b"0102030405060708"
CS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*"
RSA_KEY_B64 = "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCYEVrK/4Mahiv0pUJgTybx4J9P5dUT/Y0PuwMbk+gMU+jrZnBiXGv6/hCH1avIhoBcE535F8nJQQN3UavZdFkYidsoXuEnat3+eVTp3FslyhRwIBDF09v4vDhRtxFOT+R7uH7h/mzmyA2/+lfIMWGIrffXprYizbV76+YQKhoqFQIDAQAB"
XI = "https://global.account.xiaomi.com"
MIMO = "https://platform.xiaomimimo.com"


def gen_pw(l=12):
    while True:
        pw = ''.join(random.choice(string.ascii_letters + string.digits + "!@#$%") for _ in range(l))
        if sum([any(c.isdigit() for c in pw), any(c.isalpha() for c in pw), any(c in "!@#$%" for c in pw)]) >= 2:
            return pw


def mk_eui(email, password):
    rk = ''.join(random.choice(CS) for _ in range(16))
    ct = PKCS1_v1_5.new(RSA.import_key(base64.b64decode(RSA_KEY_B64))).encrypt(base64.b64encode(rk.encode()).decode().encode())
    rsa_b64 = base64.b64encode(ct).decode()
    kb = rk.encode()
    enc_email = base64.b64encode(AES.new(kb, AES.MODE_CBC, AES_IV).encrypt(pad(email.encode(), AES.block_size))).decode()
    enc_password = base64.b64encode(AES.new(kb, AES.MODE_CBC, AES_IV).encrypt(pad(password.encode(), AES.block_size))).decode()
    fn = base64.b64encode(b"email,password").decode()
    return f"{rsa_b64}.{fn}", enc_email, enc_password


def api(session, endpoint, email, password, extra=None):
    eui, enc_e, enc_p = mk_eui(email, password)
    data = {"email": enc_e, "password": enc_p, "region": "ID", "sid": "api-platform"}
    if extra: data.update(extra)
    r = session.post(f"{XI}/pass/{endpoint}", data=urlencode(data),
        headers={"EUI": eui, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                 "X-Requested-With": "XMLHttpRequest"})
    t = r.text.replace("&&&START&&&", "").replace("@json:", "")
    try: return json.loads(t)
    except: return {"raw": t[:500]}


def solve_captcha(session, captcha_url):
    """Get and solve captcha image via 2captcha. Only accepts >= 5 char codes."""
    if not captcha_url.startswith("http"):
        captcha_url = f"{XI}{captcha_url}"
    img = session.get(captcha_url).content
    r = requests.post("https://2captcha.com/in.php", data={
        "key": TWOCAPTCHA_KEY, "method": "base64",
        "body": base64.b64encode(img).decode(), "json": "1"})
    tid = r.json().get("request")
    for _ in range(20):
        time.sleep(2)
        p = requests.get(f"https://2captcha.com/res.php?key={TWOCAPTCHA_KEY}&action=get&id={tid}&json=1")
        if p.json().get("status") == 1:
            code = p.json()["request"]
            if len(code) >= 5:  # 4-char codes are usually wrong
                return code
    return None


def register(session, email, password, max_retries=5):
    """Register with retry on captcha failure."""
    for attempt in range(1, max_retries + 1):
        d = api(session, "sendEmailRegTicket", email, password, {"icode": ""})
        cap_url = d.get("captchaUrl", "")
        if not cap_url:
            if d.get("code") == 88205: return False  # Email blocked
            continue
        cap = solve_captcha(session, cap_url)
        if not cap: continue
        d2 = api(session, "sendEmailRegTicket", email, password, {"icode": cap})
        if d2.get("code") == 0: return True
    return False


def verify(session, email, password, code):
    """Verify email and login to MiMo."""
    d = api(session, "verifyEmailRegTicket", email, password, {"ticket": code, "icode": code})
    if d.get("code") != 0: return None
    uid = d.get("userId", "")
    # Login to MiMo
    callback = f"{MIMO}/sts?sign=M7gfywevl3CG5YTTcZDifhK6IK8=&followup={MIMO}/console/balance"
    qs = f"?callback={quote(callback, safe='')}&sid=api-platform"
    d2 = api(session, "serviceLoginAuth2", email, password, {"icode": "", "_json": "true", "qs": qs})
    loc = d2.get("location", "")
    if loc: session.get(loc, allow_redirects=True)
    return uid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", "-e", required=True)
    parser.add_argument("--password", "-p")
    parser.add_argument("--verify", help="Email verification code")
    args = parser.parse_args()
    email, password = args.email, args.password or gen_pw()
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    s.get(f"{XI}/fe/service/register/email?_locale=en_US&region=ID&sid=api-platform")
    if args.verify:
        try:
            with open("/tmp/xiaomi_session.pkl", "rb") as f: password = pickle.load(f)["password"]
        except: pass
        uid = verify(s, email, password, args.verify)
        if uid: print(f"✅ Account created! UserId: {uid}")
    else:
        if register(s, email, password):
            with open("/tmp/xiaomi_session.pkl", "wb") as f: pickle.dump({"email": email, "password": password}, f)
            print(f"✅ Email sent! Run: python3 {sys.argv[0]} -e \"{email}\" --verify <CODE>")

if __name__ == "__main__":
    main()
