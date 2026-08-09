---
name: web-api-reverse-engineering
category: software-development
description: >
  Reverse-engineer web application APIs from minified/webpack JavaScript bundles
  to build browserless automation scripts. Covers: webpack chunk analysis,
  crypto system extraction (AES/RSA/Hash), endpoint discovery, JSONP parsing,
  captcha system mapping, and request replication with Python requests.
triggers:
  - browserless signup / login / form automation
  - reverse engineer a website's API
  - replicate crypto from a web app
  - extract API endpoints from JS bundles
  - build scraper that uses a site's internal API
  - reverse-engineer authentication flow
---

# Web API Reverse Engineering

Reverse-engineer web application APIs from bundled/minified JavaScript to build
browserless automation scripts. Use when the user wants to automate a web flow
without a browser, or needs to replicate a site's crypto/auth system.

## Prerequisites

```bash
pip3 install pycryptodome requests  # AES, RSA, HTTP
```

## Step-by-step workflow

### 1. Load the target page in the browser

Use `browser_navigate` to the signup/login/form page. Then discover JS bundles:

```javascript
// browser_console expression
performance.getEntriesByType('resource')
  .filter(r => r.name.includes('.js'))
  .map(r => r.name)
```

### 2. Download and search the JS chunks

```bash
# Download all JS bundles
curl -s 'https://cdn.example.com/static/js/main.HASH.js' > /tmp/main.js

# Search for API endpoints
grep -oP '"/pass/[^"]*"' /tmp/main.js
grep -oP '"/api/[^"]*"' /tmp/main.js

# Search for crypto-related code
grep -oP '"[^"]*encrypt[^"]*"' /tmp/chunk.js
grep -oP '"[^"]*AES[^"]*"' /tmp/chunk.js

# Search for function exports (webpack module pattern)
cat /tmp/chunk.js | tr ',' '\n' | grep -iE '(encryptAes|EUI|rsa|captcha)'
```

### 3. Identify the webpack chunk architecture

Modern SPAs split code into numbered chunks. Key patterns:

- **`runtime-main.HASH.js`** — chunk loader, module registry (not useful for logic)
- **`main.HASH.js`** — app shell, routing, shared state
- **`crypto*.chunk.js`** — encryption utilities (AES, RSA)
- **`desk.*.chunk.js`** or page-specific chunks — form handlers, API calls
- Numbered chunks (`538.HASH.js`, `2395.HASH.js`) — feature-specific code

Find the crypto chunk first (search for `AES`, `encrypt`, `RSAKey`). Then find
the chunk that imports it and calls the API (search for `fetch`, `post`, `axios`).

### 4. Extract the crypto implementation

Look for these common patterns:

```javascript
// CryptoJS AES
CryptoJS.AES.encrypt(plaintext, key, {iv: iv, padding: CryptoJS.pad.Pkcs7})
CryptoJS.enc.Hex.parse("...")    // hex string → WordArray (1 byte per 2 chars)
CryptoJS.enc.Utf8.parse("...")   // utf8 string → WordArray (1 byte per char)
```

**CRITICAL PITFALL — IV encoding:** `CryptoJS.enc.Utf8.parse("0102030405060708")`
produces 16 bytes (one byte per ASCII character). `CryptoJS.enc.Hex.parse("0102030405060708")`
produces 8 bytes (two hex chars per byte). Always verify which encoder is used by
checking the module import chain in the webpack bundle. See references/cryptojs-pitfalls.md.

```javascript
// RSA (Tom Wu's RSAKey / JSEncrypt)
rsa.setPublicKey("MIGfMA0GCS...");  // base64 SPKI key (no PEM headers)
rsa.encrypt(btoa(data));             // base64 input → hex output
```

**RSA output format:** Most JS RSA libraries return hex-encoded ciphertext, not
base64. Match this in Python with `cipher.encrypt(data).hex()`.

**RSA padding:** JS RSAKey uses PKCS1 v1.5 by default. Use
`Crypto.Cipher.PKCS1_v1_5` in pycryptodome.

### 5. Discover API endpoints

Search for the API service module. In webpack, it's usually exported with
`n.d(r, {funcName: function(){return X}})`. Trace the export to the actual
`axios.post("/path", ...)` or `fetch("/path", ...)` call.

Common endpoint patterns:
```
/pass/sendServiceLoginTicket   — send verification code
/pass/serviceLoginAuth2        — unified login/register
/pass/sendEmailRegTicket       — email registration
/pass/sendPhoneRegTicket       — phone registration
/pass/tokenRegister            — token-based register
/pass/validate                 — pre-validation
/pass2/config                  — get app config
```

### 6. Map the request/response format

Look for how params are built before the API call:

```javascript
// Form-urlencoded (most common for auth APIs)
axios.post("/path", qs.stringify(params), {headers: {EUI: eui}})

// JSON body
axios.post("/path", params)

// Response parsing — watch for these prefixes:
"&&&START&&&" + JSON     // Xiaomi-style JSONP wrapper
"@json:" + JSON           // Alternative wrapper
"callback(" + JSON + ")"  // Standard JSONP
```

### 7. Build the Python script

Structure:
1. **Constants** — keys, URLs, charset, user-agent
2. **Crypto utils** — AES encrypt, RSA encrypt, hash functions
3. **API client** — session with cookies, headers, endpoint methods
4. **Captcha handler** — config detection, solver integration, manual fallback
5. **Main flow** — orchestrates the steps in order
6. **CLI** — argparse with --discover mode

Use `requests.Session()` for cookie persistence. Set `Content-Type:
application/x-www-form-urlencoded; charset=UTF-8` for form-encoded POSTs.

### 8. Captcha handling

Most sites use verify/captcha services on a separate domain. Discover the
captcha config endpoint (often loaded as a JSONP script tag). Check
`captcha-solving-and-proxying` skill for solver API integration.

## Pitfalls

1. **CryptoJS Hex vs Utf8 parse** — The string `"0102030405060708"` parsed as
   Hex gives 8 bytes; parsed as Utf8 gives 16 bytes. For AES you need 16-byte
   IVs and keys. ALWAYS trace the import to verify which encoder is used.

2. **RSA key format** — JS RSAKey.setPublicKey() takes raw base64 SPKI (no PEM
   headers). Python pycryptodome RSA.import_key() can accept DER bytes directly
   from base64 decode, or wrapped in PEM. Both work.

3. **RSA output encoding** — JS RSAKey.encrypt() returns hex. Python
   PKCS1_v1_5.encrypt() returns bytes. Convert with `.hex()` to match.

4. **JSONP response wrapping** — Auth APIs often wrap JSON in `&&&START&&&` or
   `@json:` prefixes. Strip before parsing.

5. **Webpack module tracing** — The same function name (e.g., `function I`) may
   appear in multiple modules. Always verify which module exports which function
   by checking `n.d(r, {exportName: function(){return LocalName}})`.

6. **Password handling varies** — Some auth APIs expect MD5(password).toUpperCase()
   (e.g., Xiaomi `serviceLoginAuth2` for login), while registration endpoints
   (e.g., `sendEmailRegTicket`) use AES encryption for the password. ALWAYS
   intercept the actual browser request to verify which format is used.

7. **withSearchParams** — Some SPAs merge URL query params into API request body.
   Check if the submit function calls `searchParams.get()` or spreads them in.

8. **Callback URL via `qs` parameter** — Some auth APIs (e.g., Xiaomi) reject
   `callback` parameter directly (error: "Callback连接不合法"). Instead, pass the
   full query string via `qs` parameter: `{"qs": "?callback=...&followup=...&sid=..."}`.
   The `qs` value is the raw query string from the original registration page URL.

9. **Captcha type must match endpoint** — Login endpoints accept `login` type captcha
   (`/pass/getCode?icodeType=login`), registration endpoints require `register` type.
   Using wrong type → captcha verification error. Not interchangeable.

10. **Captcha expiry timing** — Image captcha codes expire quickly. Minimize delay
     between captcha GET request and API POST. Use same session cookies. If using
     external OCR service (2captcha), the round-trip time may cause expiry.

11. **Two-phase captcha flow** — Some APIs (e.g., Xiaomi `sendEmailRegTicket`)
     require TWO requests: first without captcha (server returns captcha URL),
     then solve the captcha and resend with the code. Don't assume captcha is
     optional — the first request always fails with captcha error, but that's
     expected and part of the flow.

12. **Intercept browser requests to discover actual field names** — The JS bundle
     may show one set of parameter names (e.g., `user`, `hash`) but the ACTUAL
     form submission uses different names (e.g., `email`, `password`). Always
     intercept real XHR/fetch requests from the browser to verify:
     ```javascript
     // Install interceptor in browser_console BEFORE submitting form
     window._reqs = [];
     const origOpen = XMLHttpRequest.prototype.open;
     const origSend = XMLHttpRequest.prototype.send;
     XMLHttpRequest.prototype.open = function(m, u, ...a) {
       this._ri = {method: m, url: u, headers: {}, body: null};
       return origOpen.call(this, m, u, ...a);
     };
     XMLHttpRequest.prototype.setRequestHeader = function(n, v) {
       if (this._ri) this._ri.headers[n] = v;
       return origSetHeader.call(this, n, v);
     };
     XMLHttpRequest.prototype.send = function(body) {
       if (this._ri) { this._ri.body = body; window._reqs.push(this._ri); }
       return origSend.call(this, body);
     };
     ```
     Then submit the form and read `window._reqs` to see exact field names,
     headers (including EUI), and body format.

13. **Password encryption varies by endpoint** — Login endpoints may use MD5 hash
     while registration endpoints use AES encryption for the same password field.
     Always verify by intercepting the actual browser request.
