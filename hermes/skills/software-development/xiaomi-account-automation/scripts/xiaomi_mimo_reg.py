#!/usr/bin/env python3
"""
Xiaomi MiMo Platform - Register + Login (2-step: email code required)
Step 1: python3 xiaomi_mimo_reg.py -e "email@baru.com"
Step 2: python3 xiaomi_mimo_reg.py -e "email@baru.com" --verify 123456
"""
import argparse, base64, json, random, string, sys, time, requests, pickle
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad
from urllib.parse import urlencode, quote

API_KEY = "YOUR_2CAPTCHA_KEY"
AES_IV = b"0102030405060708"
CS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*"
EK = "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCYEVrK/4Mahiv0pUJgTybx4J9P5dUT/Y0PuwMbk+gMU+jrZnBiXGv6/hCH1avIhoBcE535F8nJQQN3UavZdFkYidsoXuEnat3+eVTp3FslyhRwIBDF09v4vDhRtxFOT+R7uH7h/mzmyA2/+lfIMWGIrffXprYizbV76+YQKhoqFQIDAQAB"
XI = "https://global.account.xiaomi.com"
MIMO = "https://platform.xiaomimimo.com"

def gen_pw(l=12):
    while True:
        pw = ''.join(random.choice(string.ascii_letters + string.digits + "!@#$%") for _ in range(l))
        if sum([any(c.isdigit() for c in pw), any(c.isalpha() for c in pw), any(c in "!@#$%" for c in pw)]) >= 2:
            return pw

def mk(e, p):
    rk = ''.join(random.choice(CS) for _ in range(16))
    ct = PKCS1_v1_5.new(RSA.import_key(base64.b64decode(EK))).encrypt(base64.b64encode(rk.encode()).decode().encode())
    rb = base64.b64encode(ct).decode()
    kb = rk.encode()
    ee = base64.b64encode(AES.new(kb, AES.MODE_CBC, AES_IV).encrypt(pad(e.encode(), AES.block_size))).decode()
    ep = base64.b64encode(AES.new(kb, AES.MODE_CBC, AES_IV).encrypt(pad(p.encode(), AES.block_size))).decode()
    return f"{rb}.{base64.b64encode(b'email,password').decode()}", ee, ep

def api(s, ep, email, pw, extra=None):
    eui, ee, ep2 = mk(email, pw)
    d = {"email": ee, "password": ep2, "region": "ID", "sid": "api-platform"}
    if extra: d.update(extra)
    r = s.post(f"{XI}/pass/{ep}", data=urlencode(d),
        headers={"EUI": eui, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "X-Requested-With": "XMLHttpRequest"})
    t = r.text.replace("&&&START&&&", "").replace("@json:", "")
    try: return json.loads(t)
    except: return {"raw": t[:300]}

def solve_cap(s, url):
    if not url.startswith("http"): url = f"{XI}{url}"
    img = s.get(url).content
    r = requests.post("https://2captcha.com/in.php", data={"key": API_KEY, "method": "base64", "body": base64.b64encode(img).decode(), "json": "1"})
    tid = r.json().get("request")
    for _ in range(20):
        time.sleep(2)
        p = requests.get(f"https://2captcha.com/res.php?key={API_KEY}&action=get&id={tid}&json=1")
        if p.json().get("status") == 1: return p.json()["request"]
    return None

def do_register(email, password):
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    s.get(f"{XI}/fe/service/register/email?_locale=id_ID&region=ID&sid=api-platform")

    print("[1/3] Captcha...")
    d = api(s, "sendEmailRegTicket", email, password, {"icode": ""})
    cap_url = d.get("captchaUrl", "")
    if not cap_url:
        print(f"    Error: {d.get('desc')}"); return False

    print("[2/3] Solving captcha...")
    cap = solve_cap(s, cap_url)
    if not cap:
        print("    Failed!"); return False
    print(f"    Code: {cap}")

    print("[3/3] Sending email...")
    d2 = api(s, "sendEmailRegTicket", email, password, {"icode": cap})
    print(f"    Result: {d2.get('code')} - {d2.get('desc')}")

    if d2.get("code") != 0:
        print(f"    Failed!"); return False

    with open("/tmp/xiaomi_reg_session.pkl", "wb") as f:
        pickle.dump({"cookies": dict(s.cookies), "email": email, "password": password}, f)

    print(f"\nEmail sent to: {email}")
    print(f"Run: python3 xiaomi_mimo_reg.py -e \"{email}\" --verify <CODE>")
    return True

def do_verify(email, code):
    try:
        with open("/tmp/xiaomi_reg_session.pkl", "rb") as f:
            saved = pickle.load(f)
    except:
        print("No session. Run without --verify first."); return False

    password = saved["password"]
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    s.cookies.update(saved["cookies"])

    print(f"Verifying code: {code}")
    eui, ee, ep = mk(email, password)
    d = api(s, "verifyEmailRegTicket", email, password, {"ticket": code})
    print(f"Result: {d.get('code')} - {d.get('desc')}")

    if d.get("code") == 0:
        uid = d.get("userId", "")
        print(f"Account created! UserId: {uid}")
        # Save credentials
        creds = {"email": email, "password": password, "userId": uid}
        with open("/root/xiaomi_mimo_credentials.json", "w") as f:
            json.dump(creds, f, indent=2)
        return True
    return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", "-e", required=True)
    parser.add_argument("--password", "-p")
    parser.add_argument("--verify", help="Verification code from email")
    args = parser.parse_args()

    if args.verify:
        do_verify(args.email, args.verify)
    else:
        password = args.password or gen_pw()
        print(f"Email: {args.email}")
        print(f"Password: {password}")
        do_register(args.email, password)

if __name__ == "__main__":
    main()
