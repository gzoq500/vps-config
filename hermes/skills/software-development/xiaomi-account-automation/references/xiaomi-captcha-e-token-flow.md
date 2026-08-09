---
name: xiaomi-captcha-e-token-flow
type: reference
---

# Xiaomi Captcha e Token Flow

Session: 2026-07-18. Extracted from `captcha-m.js` (256KB obfuscated) and live network interception.

## Overview

The captcha system uses an `e` token obtained from sensor data collection. The flow is:

1. User submits form → triggers captcha data collection
2. Browser collects fingerprint/sensor data
3. Data is encrypted (AES + RSA 2048-bit) and sent to `/captcha/v2/data`
4. Server returns URL with `e` token
5. `e` token is used for image captcha registration/verification

## Data Collection Endpoint

```
POST https://verify.sec.xiaomi.com/captcha/v2/data?k=8027422fb0eb42fbac1b521ec4a7961f&locale=en_US&_t=<timestamp>
Content-Type: application/x-www-form-urlencoded

s=<RSA_encrypted_AES_key_base64>&d=<AES_encrypted_sensor_data_base64>
```

### Response
```json
{
  "msg": "",
  "code": 0,
  "data": {
    "result": false,
    "id": "60f5700ab1654a2e9203caed7db6ec66",
    "url": "https://static-verify.sec.xiaomi.com/v2/html/check.html?t=4&k=8027422fb0eb42fbac1b521ec4a7961f&e=<ENCODED_TOKEN>&locale=en_us&eventId=<ID>"
  }
}
```

When `result: true`, the `data.token` is the captcha token (no further verification needed).
When `result: false`, the `data.url` contains the `e` token for image captcha flow.

## Encryption Format

### `s` field (RSA-encrypted AES key)
- Generate random 16-char AES key from charset: `ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*`
- Base64-encode the AES key
- RSA-encrypt the base64-encoded key with 2048-bit captcha RSA key (PKCS1v1.5)
- Base64-encode the RSA ciphertext → ~344 chars

### `d` field (AES-encrypted sensor data)
- Generate JSON sensor data (fingerprint, browser info, timestamps)
- AES-CBC encrypt with the random key, IV=`0102030405060708`, PKCS7 padding
- Base64-encode the ciphertext → ~1984 chars

### Captcha RSA Key (2048-bit, different from EUI key)
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

## Image Captcha Flow (after getting e token)

### Register
```
GET https://verify.sec.xiaomi.com/captcha/v2/image/register?e=<ENCODED_E_TOKEN>&k=8027422fb0eb42fbac1b521ec4a7961f&callback=miVerify_<TIMESTAMP>&_=<TIMESTAMP>
```

Response (JSONP):
```json
miVerify_xxx({
  "code": 0,
  "data": {
    "image": "<BASE64_JPEG>",
    "token": "<CAPTCHA_TOKEN>"
  }
})
```

### Verify
```
GET https://verify.sec.xiaomi.com/captcha/v2/image/verify?code=<SOLVED_CODE>&token=<CAPTCHA_TOKEN>&e=<ENCODED_E_TOKEN>&k=8027422fb0eb42fbac1b521ec4a7961f&callback=miVerify_<TIMESTAMP>&_=<TIMESTAMP>
```

Response (JSONP):
```json
miVerify_xxx({
  "code": 0,
  "data": {
    "result": true,
    "token": "<FLAG_TOKEN>"
  }
})
```

The `FLAG_TOKEN` is used as `icode` in `sendEmailRegTicket`.

## Key Parameters

| Parameter | Value | Source |
|-----------|-------|--------|
| `k` | `8027422fb0eb42fbac1b521ec4a7961f` | Captcha config / signup page |
| `t` | `4` (captcha type: image) | Server response |
| `locale` | `en_US` or `en_us` | Page locale |
| `e` | ~364 char URL-encoded base64 | `/captcha/v2/data` response |
| `callback` | `miVerify_<timestamp><random>` | JSONP callback name |

## Pitfalls

1. **e token expiry**: The `e` token expires in ~30 seconds. Must use immediately after capture.
2. **e token cannot be generated from Python**: The encryption format must match the browser's JS crypto exactly. Use Playwright to capture it via `page.on("response")`.
3. **k parameter is fixed**: `8027422fb0eb42fbac1b521ec4a7961f` for the signup page. May be different for other pages.
4. **JSONP format**: All captcha endpoints use JSONP. Parse with regex: `re.search(rf'{callback_name}\((.*)\)', text, re.DOTALL)`
5. **URL encoding**: The `e` token is URL-encoded in the response URL. Pass it as-is (URL-encoded) to the captcha endpoints.
6. **Simpler alternative**: The `/pass/getCode?icodeType=register` flow is more reliable and doesn't require the e token. Use that for registration.

## Playwright Capture Pattern

```python
e_token = {"value": None}

async def on_response(response):
    if '/captcha/v2/data' in response.url:
        try:
            text = await response.text()
            data = json.loads(text)
            if data.get("code") == 0 and data.get("data", {}).get("url"):
                e_match = re.search(r'[?&]e=([^&]+)', data["data"]["url"])
                if e_match:
                    e_token["value"] = e_match.group(1)  # Keep URL-encoded
        except: pass

page.on("response", on_response)
```
