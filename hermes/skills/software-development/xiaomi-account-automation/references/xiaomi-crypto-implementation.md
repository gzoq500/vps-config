---
name: xiaomi-crypto-implementation
type: reference
---

# Xiaomi Crypto Implementation Details

## Python Implementation (pycryptodome)

```python
import base64, random
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad

AES_IV = b"0102030405060708"  # UTF-8 bytes, NOT hex
CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*"
EUI_KEY_B64 = "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCYEVrK/4Mahiv0pUJgTybx4J9P5dUT/Y0PuwMbk+gMU+jrZnBiXGv6/hCH1avIhoBcE535F8nJQQN3UavZdFkYidsoXuEnat3+eVTp3FslyhRwIBDF09v4vDhRtxFOT+R7uH7h/mzmyA2/+lfIMWGIrffXprYizbV76+YQKhoqFQIDAQAB"

def mk_eui_and_encrypt(email, password):
    # 1. Generate random 16-char AES key
    rk = ''.join(random.choice(CHARSET) for _ in range(16))
    
    # 2. RSA encrypt base64(aes_key)
    ct = PKCS1_v1_5.new(
        RSA.import_key(base64.b64decode(EUI_KEY_B64))
    ).encrypt(base64.b64encode(rk.encode()).decode().encode())
    rsa_b64 = base64.b64encode(ct).decode()
    
    # 3. AES-CBC encrypt both email and password
    key_bytes = rk.encode()
    enc_email = base64.b64encode(
        AES.new(key_bytes, AES.MODE_CBC, AES_IV).encrypt(
            pad(email.encode(), AES.block_size)
        )
    ).decode()
    enc_password = base64.b64encode(
        AES.new(key_bytes, AES.MODE_CBC, AES_IV).encrypt(
            pad(password.encode(), AES.block_size)
        )
    ).decode()
    
    # 4. Build EUI: rsa_b64.base64("email,password")
    field_names = base64.b64encode(b"email,password").decode()
    eui = f"{rsa_b64}.{field_names}"
    
    return eui, enc_email, enc_password
```

## JavaScript Original (from crypto.17efe504.chunk.js)

```javascript
function Q(n) {
    n = n || {};
    var e = generateRandomKey(16);  // from CHARSET
    var o = new RSAKey();
    o.setPublicKey(PRODUCTION_KEY);
    var a = o.encrypt(btoa(e));  // RSA encrypt base64(key)
    var i = CryptoJS.enc.Utf8.parse("0102030405060708");  // IV
    var Q = CryptoJS.enc.Utf8.parse(e);  // key
    var B = btoa(Object.keys(n).join(","));  // field names
    var u = {};
    Object.keys(n).forEach(function(k) {
        u[k] = CryptoJS.AES.encrypt(n[k], Q, {iv: i, padding: CryptoJS.pad.Pkcs7}).toString();
    });
    return { EUI: a + "." + B, encryptedParams: u };
}
```

## RSA Encrypt Flow (from captcha-m.js)

```javascript
'encrypt': function(plaintext, key) {
    var keyBytes = (key.bitLength() + 7) >> 3;  // 128 for 1024-bit
    var padded = pkcs1pad2(plaintext, keyBytes);  // PKCS1 v1.5
    var result = padded.modPowInt(key.e, key.n);  // RSA
    var hex = result.toRadix(16);  // to hex
    hex = hex.padStart(keyBytes * 2, '0');  // pad to 256 chars
    return base64_encode(hex_decode(hex));  // hex → bytes → base64
}
```

## Captcha RSA Key (from captcha-m.js, 2048-bit)

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

## Critical Discovery: Field Names

The **most common mistake** is using wrong field names. The browser sends:
- `email` (NOT `user`) — AES-encrypted email
- `password` (NOT `hash`) — AES-encrypted password (NOT MD5!)
- `email,password` in EUI field names (NOT just `user`)

This was discovered by intercepting actual browser XHR requests via:
```javascript
// Install interceptor on page
const origSend = XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.send = function(body) {
  window._capturedRequests.push({body: body});
  return origSend.call(this, body);
};
```

## Error Codes

| Code | Description | Meaning |
|------|-------------|---------|
| 0 | 成功 | Success |
| 70014 | 验证码错误 | Verification code wrong |
| 70016 | 登录验证失败 | Login verification failed |
| 81004 | 公钥不合法 | Public key illegal (wrong EUI format) |
| 87001 | 验证码输入错误 | Captcha verification error |
| 88205 | 非法的邮件地址 | Illegal email address |
| 10017 | 参数值非法 | Parameter value illegal |
| 10025 | Callback连接不合法 | Callback URL illegal |
