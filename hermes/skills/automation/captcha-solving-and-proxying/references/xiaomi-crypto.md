# Xiaomi Account Signup Crypto Analysis

## Source Files (from `cdn.web-global.fds.api.mi-img.com/mcfe--mi-account/static/static/js/`)

- `crypto.js` — AES + RSA encryption functions
- `crypto-util.7ebfad42.js` — AES-CBC implementation (CryptoJS)
- `fingerprintjs.e8cc27b2.chunk.js` — Browser fingerprint collection
- `captcha-m.js` — Captcha SDK (GeeTest + reCAPTCHA + Image)
- `captcha-v.js` — Captcha verification logic

## AES Encryption (encryptAes function)

```javascript
function encryptAes(params) {
    // 1. Generate random 16-char key
    var charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*";
    var randomKey = generateRandomKey(16, charset);
    
    // 2. RSA-encrypt the base64'd key
    var rsa = new RSAKey();
    rsa.setPublicKey(EUI_PUBLIC_KEY);
    var encryptedKey = rsa.encrypt(btoa(randomKey));
    
    // 3. AES-CBC encrypt each param value
    var iv = CryptoJS.parse("0102030405060708"); // hardcoded
    var key = CryptoJS.parse(randomKey);
    var encryptedParams = {};
    Object.keys(params).forEach(function(k) {
        encryptedParams[k] = CryptoJS.AES.encrypt(
            params[k], key, {iv: iv, padding: CryptoJS.pad.Pkcs7}
        ).toString();
    });
    
    // 4. EUI = RSA_encrypted_key + "." + base64(field_names)
    return {
        EUI: encryptedKey + "." + btoa(Object.keys(params).join(",")),
        encryptedParams: encryptedParams
    };
}
```

## RSA Public Keys (Production)

### EUI Key (encrypts AES key, 1024-bit RSA)
```
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCYEVrK/4Mahiv0pUJgTybx4J9P5dUT/Y0PuwMbk+gMU+jrZnBiXGv6/hCH1avIhoBcE535F8nJQQN3UavZdFkYidsoXuEnat3+eVTp3FslyhRwIBDF09v4vDhRtxFOT+R7uH7h/mzmyA2/+lfIMWGIrffXprYizbV76+YQKhoqFQIDAQAB
```

### RSA Param Key (encrypts individual field values, 1024-bit RSA)
```
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCHcPEm9Wo8/LWHL8mohOV5YalTgZLzng+nWCEkIRP//6GohYlIh3dvGpueJvQ3Sany/3dLx0x6MQKA34NxRyoO37R/LgPZUfe6eWzHQeColBBHxTEDbCqDh46Gv5vogjqHRl4+q2WGCmZOIfmPjNHQWG8sMI...
```

### Captcha RSA Key (different from crypto keys, 2048-bit)
```
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArxfNLkuAQ/BYHzkzVwtu
g+0abmYRBVCEScSzGxJIOsfxVzcuqaKO87H2o2wBcacD3bRHhMjTkhSEqxPjQ/FE
XuJ1cdbmr3+b3EQR6wf/cYcMx2468/QyVoQ7BADLSPecQhtgGOllkC+cLYN6Md34
Uii6U+VJf0p0q/saxUTZvhR2ka9fqJ4+6C6cOghIecjMYQNHIaNW+eSKunfFsXVU
+QfMD0q2EM9wo20aLnos24yDzRjh9HJc6xfr37jRlv1/boG/EABMG9FnTm35xWrV
R0nw3cpYF7GZg13QicS/ZwEsSd4HyboAruMxJBPvK3Jdr4ZS23bpN0cavWOJsBqZ
VwIDAQAB
-----END PUBLIC KEY-----
```

### Preview vs Production
Preview host: `account.preview.n.xiaomi.net` uses different RSA keys.
Production host: `global.account.xiaomi.com` uses the keys above.

## Captcha System

### Hosts
- Production: `https://verify.sec.xiaomi.com`
- Static: `https://static.verify.sec.xiaomi.com`
- Static CDN: `https://cdn.cnbj1.fds.api.mi-img.com/captcha/0.73/m.js`
- Staging: `https://infosec-captcha-staging.pt.xiaomi.com`

### Endpoints
- `/captcha/v2/data/lv` — data collection (fingerprint)
- `/captcha/v2/data` — data collection
- `/captcha/v2/image/register` — get image captcha (returns base64 image)
- `/captcha/v2/image/verify` — verify image captcha code
- `/captcha/v2/gt/dk/verify` — GeeTest slide/click verify
- `/captcha/v2/recaptcha/verify` — reCAPTCHA verify

### Captcha Types (VERIFY_TYPE)
| Type | ID | Description |
|------|-----|-------------|
| SLIDE | 1 | GeeTest slide |
| CLICK | 2 | GeeTest click |
| CAPTCHA | 3 | Image captcha |
| RECAPTCHA | 4 | reCAPTCHA v2 visible |
| RECAPTCHA_INVISIBLE | 5 | reCAPTCHA invisible |
| CLICK_WORD | 6 | Click word |
| CLICK_ICON | 7 | Click icon |
| SPACE | 8 | Space |
| GRID | 9 | Grid |
| VOICE | 10 | Voice |

### reCAPTCHA Site Keys
- Visible: `6LeBM0ocAAAAAEwYcFUjtxpVbs-0rnbSVXBBXmh4`
- Invisible: `6LeGW00cAAAAAG92ZOn8W3YAcy3jJifCuhy5iDvg`

### GeeTest Config
- gt: `050cffef4ae57b5d5e529fea9540b0d1`
- challenge: `3bd38408ae4af923ed36e13819b14d42`
- api_server: `yumchina.geetest.com`

### Captcha Flow
1. Initial data collection (`/captcha/v2/data`) with fingerprint
2. Server responds with captcha type + config
3. If image captcha: register → get image → user enters code → verify
4. If GeeTest: init GeeTest SDK → user solves slide/click → verify with challenge+seccode
5. If reCAPTCHA: load enterprise.js → render widget → user solves → verify with g-recaptcha-response
6. On success: returns `flag` token (used in signup API call)

### Captcha Parameters
- `e` — captcha session token
- `k` — captcha key
- `c` — GeeTest challenge
- `l` — GeeTest gt value
- `t` — captcha type
- `flag` — verification result token
- `a` — action string
- `uid` — user ID
- `locale` — language

## Fingerprint Collection

The captcha SDK collects extensive browser fingerprint data:
- Canvas fingerprint
- WebGL fingerprint (renderer, vendor, extensions, precision)
- Screen resolution, color depth
- Timezone, language
- Installed plugins, fonts
- Touch support
- WebDriver detection
- WebRTC IP leak

Data is sent to `/captcha/v2/data` endpoint before captcha is shown.

## Signup Page Structure

- URL: `https://global.account.xiaomi.com/fe/service/register/email`
- Fields: email, password, confirmPassword, agreement checkbox
- After "Next": encrypts fields with AES, creates EUI, sends to signup API
- Signup API endpoint: `POST /pass/serviceLoginAuth2` (verified 2026-07-17)
- Known path patterns: `/pass/getCode?icodeType=`, `/pass/logout?userId=`

## Verified Registration Flow (2026-07-17)

### Working Approach
1. Load registration page → get cookies
2. `GET /pass/getCode?icodeType=login` → get image captcha
3. Solve captcha via 2captcha API (`POST /in.php`, method=base64)
4. `POST /pass/serviceLoginAuth2` with:
   - `sid=passport`
   - `user=<AES_encrypted_email>`
   - `cc=ID`
   - `hash=<MD5(password).toUpperCase()>`
   - `_json=true`
   - `policyName=privacy_policy_register_email`
   - `captCode=<solved_captcha_code>`
   - `qs=?callback=...&followup=...&sid=api-platform` (NOT `callback` parameter)
   - Header: `EUI: <eui_string>`

### Critical Pitfalls
1. **`qs` vs `callback`**: Use `qs` parameter for callback URL, NOT `callback` directly
2. **Captcha type**: `serviceLoginAuth2` accepts `login` type captcha, NOT `register`
3. **Captcha expiry**: Image captcha expires quickly — minimize delay between solve and use
4. **Same session**: Must use same `requests.Session()` for captcha GET and API POST

### 2captcha Integration for Xiaomi
```python
# Upload image captcha
r = requests.post("https://2captcha.com/in.php", data={
    "key": API_KEY, "method": "base64",
    "body": base64.b64encode(captcha_image_bytes).decode(), "json": "1"
})
task_id = r.json()["request"]

# Poll for result
while True:
    time.sleep(3)
    r = requests.get(f"https://2captcha.com/res.php?key={API_KEY}&action=get&id={task_id}&json=1")
    if r.json()["status"] == 1:
        captcha_code = r.json()["request"]  # e.g., "KYXHX"
        break

# For reCAPTCHA Enterprise
r = requests.post("https://2captcha.com/in.php", data={
    "key": API_KEY, "method": "userrecaptcha",
    "googlekey": "6LeBM0ocAAAAAEwYcFUjtxpVbs-0rnbSVXBBXmh4",
    "pageurl": "https://global.account.xiaomi.com/fe/service/register/email",
    "enterprise": "1", "json": "1"
})
```

### Error Codes (Verified)
| Code | Description | Meaning |
|------|-------------|---------|
| 0 | Success | Registration successful |
| 70016 | 登录验证失败 | Email not registered or wrong password |
| 81004 | 公钥不合法 | EUI header malformed |
| 87001 | 验证码输入错误 | Captcha code wrong or expired |
| 10025 | Callback连接不合法 | Use `qs` parameter instead of `callback` |

## Status

- ✅ Crypto fully analyzed (AES + RSA keys extracted)
- ✅ Captcha system mapped (endpoints, types, keys)
- ✅ Registration endpoint found: `POST /pass/serviceLoginAuth2`
- ✅ Callback parameter: use `qs` not `callback`
- ✅ Image captcha solving via 2captcha works (login type)
- ⚠️ OCR accuracy issues with some captcha images
- ⚠️ reCAPTCHA Enterprise token not accepted by `serviceLoginAuth2` (needs image captcha)
