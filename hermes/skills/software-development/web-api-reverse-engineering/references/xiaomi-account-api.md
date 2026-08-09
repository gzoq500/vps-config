# Xiaomi Account API — Reverse-Engineered Details

Session: 2026-07-17. All details extracted from live webpack bundles on
`cdn.web-global.fds.api.mi-img.com/mcfe--mi-account/static/`.

## JS Bundle Architecture

| File | Purpose |
|------|---------|
| `runtime-main.HASH.js` | Chunk loader |
| `main.HASH.js` | App shell, routing (~29KB) |
| `crypto-util.HASH.js` | CryptoJS library (AES, CBC, PKCS7) |
| `crypto.HASH.chunk.js` | App-level encryptAes() and rsa() functions (~2KB) |
| `5721.HASH.chunk.js` | API service module — all /pass/* endpoint wrappers |
| `2395.HASH.chunk.js` | Email registration form handler and flow |
| `538.HASH.chunk.js` | Phone registration flow |
| `DHome.HASH.chunk.js` | Login/register page shell |
| `fingerprintjs.HASH.chunk.js` | FingerprintJS for device fingerprinting |

## Module Dependency Chain for Email Registration

```
2395.chunk.js (form handler)
  └─ imports module 73329 from 5721.chunk.js (API service)
  └─ lazy-loads modules [2605, 8132, 695, 7634]
       └─ 7634 = crypto.chunk.js (encryptAes)
            └─ module 695 = RSA implementation (X class)
            └─ module 10886 = CryptoJS.enc.Utf8
            └─ module 12440 = CryptoJS.pad.Pkcs7
```

## API Endpoints (module 73329 in 5721.chunk.js)

```
By → I → POST /pass/sendServiceLoginTicket   (send verification code — LOGIN only)
Js → N → POST /pass/serviceLoginAuth2        (unified login — NOT for registration)
$i → M → POST /pass/sendEmailRegTicket       (EMAIL REGISTRATION — use this)
Z7 → U → POST /pass/verifyEmailRegTicket     (verify email reg ticket)
pH → T → POST /pass/tokenRegister            (token-based register)
K9 → z → POST /pass/sms/quota               (SMS quota check)
HH → V → POST /pass/preference              (user preferences)
Gu → J → POST /pass/validate                (pre-validation)
Q2 → P → GET  /pass2/config?key=login&key=register (app config)
V8 → B → POST /pass/sendPhoneRegTicket      (send phone reg ticket)
Mg → H → POST /pass/verifyRegPhone          (verify phone reg)
```

All POST endpoints use `Content-Type: application/x-www-form-urlencoded; charset=UTF-8`.

## Encryption System (from crypto.17efe504.chunk.js)

### encryptAes(params) → {EUI, encryptedParams}

```python
# 1. Random 16-char key from charset
CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*"

# 2. IV parsed as UTF-8 (NOT hex!) — produces 16 bytes
IV = b"0102030405060708"

# 3. Key parsed as UTF-8 — produces 16 bytes
key_bytes = random_key.encode("utf-8")

# 4. RSA encrypt base64(key) with EUI key → base64 string
EUI_RSA_KEY = "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCYEVrK/4M..."  # 1024-bit SPKI
# JS RSA encrypt returns: hex(ciphertext) → pad to 256 chars → hex_decode → base64
# Which equals: base64(ciphertext)
encrypted_key = base64(rsa_encrypt(base64(key).encode(), eui_rsa_key))

# 5. Base64 of field names joined by comma
field_names = base64(",".join(params.keys()))

# 6. AES-CBC encrypt each value
encrypted[k] = aes_cbc_encrypt(value, key_bytes, iv_bytes)  # returns base64

# 7. EUI = base64(RSA_ciphertext) + "." + base64(field_names)
```

### RSA Key (EUI — production)

```
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCYEVrK/4Mahiv0pUJgTybx4J9P5dUT
/Y0PuwMbk+gMU+jrZnBiXGv6/hCH1avIhoBcE535F8nJQQN3UavZdFkYidsoXuEnat3+e
VTp3FslyhRwIBDF09v4vDhRtxFOT+R7uH7h/mzmyA2/+lfIMWGIrffXprYizbV76+YQKh
oqFQIDAQAB
```

### RSA Key (param encryption — production)

```
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCHcPEm9Wo8/LWHL8mohOV5YalTgZLz
ng+nWCEkIRP//6GohYlIh3dvGpueJvQ3Sany/3dLx0x6MQKA34NxRyoO37R/LgPZUfe6
eWzHQeColBBHxTEDbCqDh46Gv5vogjqHRl4+q2WGCmZOIfmPjNHQWG8sMIZyTqFCLc6g
k9vSewIDAQAB
-----END PUBLIC KEY-----
```

## Email Registration Flow (Verified Working 2026-07-17)

**CRITICAL CORRECTIONS from live browser interception:**

### Two-Phase Captcha Flow

The registration uses a TWO-PHASE captcha flow:

```
Phase 1: Send request WITHOUT captcha → server returns captcha URL
Phase 2: Get captcha image, solve it, resend WITH captcha code
```

### Complete Verified Flow

```
1. Load /fe/service/register/email?_locale=id_ID&region=ID&sid=api-platform
   → get cookies (uLocale, ick)

2. POST /pass/sendEmailRegTicket  (first attempt, no captcha)
   Body: email=<AES_encrypted_email>
         &password=<AES_encrypted_password>
         &region=ID
         &sid=api-platform
         &icode=
   Header: EUI: <eui_string>
           Content-Type: application/x-www-form-urlencoded; charset=UTF-8
           X-Requested-With: XMLHttpRequest
   Response: {"code":87001, "captchaUrl":"/pass/getCode?icodeType=register"}

3. GET https://global.account.xiaomi.com{captchaUrl}
   → returns JPEG image (125x42 pixels)

4. Solve captcha via 2captcha (file upload method works best):
   POST https://2captcha.com/in.php
   files={"file": ("captcha.jpg", image_bytes, "image/jpeg")}
   data={"key": API_KEY, "json": "1"}
   Poll /res.php until status=1 → captcha code

5. POST /pass/sendEmailRegTicket  (second attempt, with captcha)
   Body: email=<AES_encrypted_email>
         &password=<AES_encrypted_password>
         &region=ID
         &sid=api-platform
         &icode=<captcha_code>
   Header: EUI: <eui_string>
           Content-Type: application/x-www-form-urlencoded; charset=UTF-8
           X-Requested-With: XMLHttpRequest
   Response: {"code":0, "data":{"address":"heg***@r***l.biz.id","vCodeLen":6}}

6. User checks email → gets 6-digit verification code

7. POST /pass/verifyEmailRegTicket → Account created!
```

### encryptAes for Registration — Field Names

For `sendEmailRegTicket`, the encryptAes function encrypts BOTH email and password:

```python
def mk_eui_and_encrypt(email, password):
    rk = random_key(16)  # from CHARSET
    # RSA encrypt base64(key)
    ct = PKCS1_v1_5.new(rsa_key).encrypt(base64(rk).encode())
    rsa_b64 = base64(ct).decode()
    # AES encrypt BOTH fields with SAME key
    enc_email = base64(AES.new(rk.encode(), CBC, IV).encrypt(pad(email.encode())))
    enc_password = base64(AES.new(rk.encode(), CBC, IV).encrypt(pad(password.encode())))
    # EUI field names include BOTH
    field_names = base64("email,password")  # NOT just "user"!
    return f"{rsa_b64}.{field_names}", enc_email, enc_password
```

### PITFALL: Field Names Are `email` and `password` (not `user`/`hash`)

The browser sends `email` and `password` fields to `sendEmailRegTicket`, NOT
`user` and `hash`. Using wrong field names causes:
- `81004: 公钥不合法` (EUI field names mismatch)
- `87001: 验证码输入错误` (server can't parse the request)

### PITFALL: Password Is AES-Encrypted (not MD5)

For `sendEmailRegTicket`, the password is AES-encrypted with the same key as
the email. For `serviceLoginAuth2` (login only), the password IS MD5-hashed.

### `serviceLoginAuth2` vs `sendEmailRegTicket`

| Endpoint | Purpose | Password | Fields | Captcha Type |
|----------|---------|----------|--------|--------------|
| `serviceLoginAuth2` | LOGIN | AES encrypted | `email`, `password` | `login` |
| `sendEmailRegTicket` | REGISTER | AES encrypted | `email`, `password` | `register` |

Do NOT use `serviceLoginAuth2` for registration — it's a login-only endpoint.
Returns `70016: 登录验证失败` if email not registered.

### Callback via `qs` Parameter

Some endpoints reject `callback` parameter directly:
```
{"code": 10025, "desc": "Callback连接不合法"}
```

Instead, pass the full query string via `qs` parameter:
```
qs=?callback=https://platform.xiaomimimo.com/sts?sign=M7gfywevl3CG5YTTcZDifhK6IK8%3D&followup=https://platform.xiaomimimo.com/console/balance&sid=api-platform
```

### Captcha Type Distinction

- `serviceLoginAuth2` → `login` type captcha (`/pass/getCode?icodeType=login`)
- `sendEmailRegTicket` → `register` type captcha (`/pass/getCode?icodeType=register`)
- Using wrong type → `87001: 验证码输入错误`
- Both types solvable via 2captcha file upload method

### Error Codes (Verified Live)

| Code | Description | Meaning |
|------|-------------|---------|
| 0 | Success | Registration/login successful |
| 302 | Redirect | Success with redirect URL |
| 70008 | 电话号码格式错误 | Phone number format error (wrong endpoint for email) |
| 70016 | 登录验证失败 | Login verification failed — email not registered or wrong password |
| 81004 | 公钥不合法 | Public key illegal — EUI header malformed or wrong field names |
| 87001 | 验证码输入错误 | Captcha code incorrect or expired |
| 10017 | 参数值非法 | Parameter value illegal |
| 10025 | Callback连接不合法 | Callback URL format wrong — use `qs` instead |

## Captcha System

- Config: `https://verify.sec.xiaomi.com/captcha/v2/config?type=1&locale=en_US&callback=miVerify_xxx`
- Data collection: `POST /captcha/v2/data/lv`
- Image captcha: `GET /captcha/v2/image/register` → `POST /captcha/v2/image/verify`
- **reCAPTCHA Enterprise** (verified 2026-07-17): Sitekey `6LeBM0ocAAAAAEwYcFUjtxpVbs-0rnbSVXBBXmh4`. Appears as iframe AFTER form submission. Loaded via `enterprise.js`.
- reCAPTCHA site key (invisible): `6LeGW00cAAAAAG92ZOn8W3YAcy3jJifCuhy5iDvg`
- GeeTest config: gt=`050cffef4ae57b5d5e529fea9540b0d1`, challenge=`3bd38408ae4af923ed36e13819b14d42`
- Captcha RSA key (2048-bit, different from crypto keys): `MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArxfNLkuAQ/BYHzkzVwtu...`

## Response Format

Responses use `&&&START&&&` JSON prefix or `@json:` prefix. Strip before parsing.

## Verify Email Registration (verifyEmailRegTicket)

After `sendEmailRegTicket` succeeds (code=0), the `captchaToken` cookie is set.

### Ticket Parameter
The `verifyEmailRegTicket` endpoint requires a `ticket` parameter:
- **Email code** (6-digit from inbox) — RELIABLE, always works
- **captchaToken cookie value** — UNRELIABLE, returns `70014` most of the time

**Always use the email verification code** as the `ticket` parameter for reliable automation.

### Request Format
```
POST /pass/verifyEmailRegTicket
Body: email=<encrypted>&password=<encrypted>&region=ID&sid=api-platform&ticket=<email_code>&icode=<email_code>
Header: EUI: <eui_string>
```

Note: Both `ticket` and `icode` should be set to the email verification code.

### Success Response
```json
{
  "code": 0,
  "userId": "6883964840",
  "location": "https://account.xiaomi.com/pass/serviceLogin?sid=api-platform&callback"
}
```

### Rate Limiting
- `20332`: Per-hour limit (~5 sends per email). Wait ~1 hour.
- "Sent too many codes. Try again tomorrow.": 24-hour block per email. Cannot bypass.
- `88205`: Email domain blacklisted or already registered.

## Scripts

- `/root/xiaomi_final.py` — ⭐ BEST: Browserless register + verify with retry logic (skips 4-char captcha codes)
- `/root/xiaomi_signup_browserless.py` — Full browserless signup script (1121 lines)
- `/root/xiaomi_mimo_reg.py` — 2-step registration (register → verify with email code)
- `/root/xiaomi_analysis/` — Downloaded JS bundles for analysis
- `/root/xiaomi_backup_20260718/` — Backup of all working scripts
