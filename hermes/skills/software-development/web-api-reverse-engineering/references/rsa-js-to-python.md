# RSA in JS vs Python — Mapping Guide

## JS RSA Libraries → Python Equivalents

### Tom Wu's RSAKey (used by JSEncrypt and many sites)

```javascript
var rsa = new RSAKey();
rsa.setPublicKey("MIGfMA0GCS...");  // base64 SPKI, no PEM headers
var encrypted = rsa.encrypt(btoa("plaintext"));  // returns HEX string
```

**Python (pycryptodome):**
```python
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import base64

# Import the key — base64 SPKI works directly
der_bytes = base64.b64decode("MIGfMA0GCS...")
rsa_key = RSA.import_key(der_bytes)

# Encrypt — PKCS1v1.5 padding (default in JS RSAKey)
cipher = PKCS1_v1_5.new(rsa_key)
ciphertext = cipher.encrypt(b"plaintext")

# JS returns hex, so convert
hex_result = ciphertext.hex()
```

### JSEncrypt

```javascript
var encrypt = new JSEncrypt();
encrypt.setPublicKey(pem_string);  // full PEM with headers
var encrypted = encrypt.encrypt("plaintext");  // base64 string
```

**Note:** JSEncrypt returns **base64** (not hex like RSAKey). Check which
library the target site uses.

### node-rsa

```javascript
var NodeRSA = require('node-rsa');
var key = new NodeRSA(pem_string);
var encrypted = key.encrypt("plaintext", "base64");  // output format chosen by caller
```

## Key Format Conversion

### SPKI base64 → PEM
```python
import base64
b64_key = "MIGfMA0GCS..."
pem = f"-----BEGIN PUBLIC KEY-----\n{b64_key}\n-----END PUBLIC KEY-----"
# or with line breaks every 64 chars
```

### PEM → DER bytes
```python
from Crypto.PublicKey import RSA
key = RSA.import_key(pem_string)
der_bytes = key.export_key(format='DER')
```

### Extract modulus and exponent
```python
key = RSA.import_key(der_bytes)
print(f"n = {hex(key.n)}")
print(f"e = {hex(key.e)}")  # usually 65537 = 0x10001
```

## Common Pitfalls

1. **Padding mismatch:** JS RSAKey uses PKCS1v1.5 by default. Some sites use
   OAEP. Check the JS source for `RSAKey.prototype.encrypt` — if it calls
   `pkcs1pad2`, it's v1.5. Use `PKCS1_v1_5` in Python.

2. **Input encoding:** JS `btoa()` produces base64. If the site RSA-encrypts
   the base64 of the key (not the raw key), you must do the same in Python:
   `cipher.encrypt(base64.b64encode(raw_data))`.

3. **Output encoding mismatch:**
   - RSAKey.encrypt() → hex string
   - JSEncrypt.encrypt() → base64 string
   - SubtleCrypto.encrypt() → ArrayBuffer (binary)
   Always verify by checking the library source or network tab.

4. **Key size limits:** PKCS1v1.5 with 1024-bit key can encrypt at most
   117 bytes (128 - 11). With 2048-bit: 245 bytes. If the plaintext is
   too long, the JS library silently fails (returns empty string or false).
   Check `plaintext.length <= key_size_bytes - 11`.

5. **Trailing null bytes:** Some JS RSA implementations strip trailing nulls.
   pycryptodome does not. If decryption mismatches, try `.rstrip(b'\x00')`.
