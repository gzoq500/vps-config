# CryptoJS Pitfalls for Python Replication

CryptoJS is the most common JS crypto library. Replicating its behavior in Python
requires understanding these non-obvious behaviors.

## Parse Methods — The #1 Source of Bugs

CryptoJS has multiple "enc" (encoder) modules that convert strings to WordArrays:

```javascript
CryptoJS.enc.Hex.parse("0102030405060708")
// → WordArray [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08]
// = 8 bytes (two hex chars → one byte)

CryptoJS.enc.Utf8.parse("0102030405060708")
// → WordArray [0x30, 0x31, 0x30, 0x32, 0x30, 0x33, 0x30, 0x34,
//              0x30, 0x35, 0x30, 0x36, 0x30, 0x37, 0x30, 0x38]
// = 16 bytes (each ASCII char → one byte)
```

**How to determine which is used:** In webpack bundles, the parse function comes
from a module import:
```javascript
var c = n(10886);  // module 10886 = CryptoJS.enc.Utf8 (or Hex)
// ...
var iv = c().parse("0102030405060708");
```
Trace the module ID back to find which encoder it wraps. If the string contains
only hex chars (0-9, a-f), it COULD be either — you must check the source.

**Rule of thumb:** If the parsed result needs to be exactly 16 bytes for AES,
and the string is 16 ASCII characters, it's Utf8. If it's 32 hex characters, it's Hex.

## AES Output Format

`CryptoJS.AES.encrypt(...).toString()` returns **base64-encoded ciphertext**
(OpenSSL format when no salt). This is NOT hex.

Python equivalent:
```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64

cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
ct = cipher.encrypt(pad(plaintext.encode(), 16))
b64_result = base64.b64encode(ct).decode()  # matches .toString()
```

## Default Padding and Mode

CryptoJS AES defaults:
- Mode: CBC
- Padding: PKCS7 (same as PKCS5 for 16-byte blocks)
- Output: base64 via `.toString()`, WordArray via `.toString(CryptoJS.enc.Hex)`

## Key Size Detection

CryptoJS auto-detects key size from the WordArray:
- 4 words (16 bytes) → AES-128
- 6 words (24 bytes) → AES-192
- 8 words (32 bytes) → AES-256

If you pass a string as the key, CryptoJS uses Password-Based Key Derivation
(EvpKDF), NOT the raw bytes. Always use `.parse()` to pass raw key bytes.

## Common Wiring Mistakes in Bundles

Webpack bundles often alias CryptoJS modules:
```javascript
var r = t.n(o);  // r() = CryptoJS.AES
var c = t.n(a);  // c() = CryptoJS.enc.Utf8
var i = t.n(i);  // i() = CryptoJS.pad.Pkcs7
```
The `.n()` wrapper handles ES module default export interop. `t.n(x)` returns
a function that returns `x.default || x`.
