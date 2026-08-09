# MiMo Browserless STS Flow — Complete Reference

## Status: PARTIALLY WORKING (Steps 1-5 confirmed, Step 6 unresolved — NEW: `?ref=` URL approach untested)

## The Problem

MiMo platform API (`/api/v1/invitation/bind`) requires authentication. Previous approaches failed because:
- Playwright can't render the invite SPA in headless mode
- `serviceLoginAuth2` returns 70016 (needs email verification first)
- Hardcoded STS `sign` parameter is always stale/expired
- MiMo uses JavaScript-set session cookies that Python requests can't replicate

## The Flow (6 Steps — all in ONE `requests.Session()`)

### Step 1: Verify Email
```python
eui, enc_e, enc_p = mk_eui(email, password)
r = s.post(f'{XI}/pass/verifyEmailRegTicket', data=urlencode({
    'email': enc_e, 'password': enc_p, 'region': 'ID', 'sid': 'api-platform',
    'ticket': EMAIL_CODE, 'icode': EMAIL_CODE
}), headers={'EUI': eui, 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest'})
j = json.loads(r.text.replace('&&&START&&&', ''))
# j['code'] == 0, j['userId'] == '688...', j['user_synced_url'] == 'https://...'
```

### Step 2: userSynced (SAME SESSION!)
```python
synced_url = j['user_synced_url']
r2 = s.get(synced_url, allow_redirects=True)
# Response: {"code":0,"result":"ok","description":"成功","data":"{}"}
# Cookies SET: passToken, cUserId, userId, passInfo (domain=.account.xiaomi.com)
# passToken format: "V1:DXmurwq2/R1BHTELu6obCf5SEsEWZHG7hDkYw6Ue2BSwOcb..."
```

**CRITICAL**: userSynced only sets passToken when called in the SAME session as verifyEmailRegTicket. A fresh session gets code=0 but NO cookies. The `_sign` parameter is REQUIRED (returns 10017 without it).

### Step 3: Get loginUrl from 401
```python
r3 = s.post(f'{MIMO}/api/v1/invitation/bind', json={'code': 'REFERRAL_CODE'},
    headers={'Content-Type': 'application/json'})
# Returns: {"code":401, "loginUrl":"https://account.xiaomi.com/pass/serviceLogin?callback=https%3A%2F%2Fplatform.xiaomimimo.com%2Fsts%3Fsign%3DFRESH_SIGN%26followup%3D..."}
login_url = r3.json()['loginUrl']
```

### Step 4: Follow loginUrl → STS redirect (DO NOT MODIFY loginUrl!)
```python
url = login_url  # MUST use as-is! sign is tied to followup URL.
for step in range(10):
    if not url: break
    r = s.get(url, allow_redirects=False)
    sc = r.headers.get('Set-Cookie', '')
    if 'serviceToken' in sc:
        m = re.search(r'api-platform_serviceToken="?([^";]+)', sc)
        if m: service_token = m.group(1)
    loc = r.headers.get('Location', '')
    url = loc
```

**STS redirect chain:**
```
302 → platform.xiaomimimo.com/sts?sign=...&followup=...&auth=VALID_AUTH
  → Sets serviceToken cookie
307 → http://platform.xiaomimimo.com/api/v1/invitation/bind?userId=...  (HTTP!)
307 → https://platform.xiaomimimo.com/api/v1/invitation/bind?userId=...
400 → (Bad Request — GET to POST-only endpoint, but serviceToken IS validated)
```

The 400 response confirms the serviceToken is valid — the endpoint just needs a POST body.

### Step 5: Call invite API (⚠️ UNRESOLVED — returns 401)
```python
# Tried multiple cookie delivery methods — ALL return 401:
# A: Session cookies
r5 = s.post(f'{MIMO}/api/v1/invitation/bind', json={'code': 'QB3238'},
    headers={'Content-Type': 'application/json'})

# B: Explicit Cookie header (unquoted)
requests.post(url, json={'code':'QB3238'},
    headers={'Cookie': f'api-platform_serviceToken={token}', ...})

# C: Explicit Cookie header (quoted)
requests.post(url, json={'code':'QB3238'},
    headers={'Cookie': f'api-platform_serviceToken="{token}"', ...})

# D: Combined passToken + serviceToken
# E: All session cookies concatenated
# ALL return 401
```

## Cookie Flow

| Step | Domain | Cookies Set |
|------|--------|-------------|
| userSynced | .account.xiaomi.com | passToken, cUserId, userId, passInfo |
| serviceLogin redirect | account.xiaomi.com | pass_ua, deviceId |
| STS redirect | platform.xiaomimimo.com | serviceToken |

## Key Parameters

- **passToken**: Session-bound, minted by userSynced using verify context
- **cUserId**: Cross-service user ID (format: CVGgElQQaEg4m-...)
- **serviceToken**: Platform-specific auth token (set by STS)
- **sign**: Fresh per-request in loginUrl, never hardcode
- **auth**: STS-specific validation token in redirect URL

## Unsolved Mystery

The serviceToken IS valid (STS redirect to invite API returns 400, not 401). But subsequent POST requests with the same token return 401. Possible causes:
1. ServiceToken bound to specific redirect context (can't be reused)
2. Zero TTL (expires immediately after redirect)
3. Additional CSRF/session mechanism not captured
4. Cookie domain/path mismatch between STS set and API send
5. HTTP→HTTPS redirect affects cookie handling (Secure flag)
6. **NEW HYPOTHESIS (2026-07-18)**: The STS response `Set-Cookie` header likely has specific `Domain`, `Path`, `Secure`, `HttpOnly`, and `SameSite` attributes that prevent `requests` from sending the cookie correctly. **Next step: capture the RAW `Set-Cookie` header from the STS response** using `r.headers.get('Set-Cookie')` and check all attributes.

## New Pitfalls (2026-07-18 session)

| # | Pitfall | Details |
|---|---------|---------|
| 1 | passToken manual setting rejected | Setting passToken via `s.cookies.set('passToken', PT, domain='.account.xiaomi.com')` does NOT work. Server redirects loginUrl to login page instead of STS. The passToken must be set by the server via `userSynced` in the same session. |
| 2 | STS sign tied to followup | Modifying the `followup` URL in the loginUrl's callback parameter invalidates the sign. STS returns 401. Always use loginUrl AS-IS. |
| 3 | STS redirect chain is HTTP-first | The STS redirect goes to `http://` before `https://`. This may cause cookie loss if `Secure` flag is set. |
| 4 | serviceLoginAuth2 returns 70016 for verified accounts | Even after successful API verification, `serviceLoginAuth2` still returns 70016. The account requires browser-based identity verification via the verifyEmail page. |
| 5 | Verification codes are single-use | Each code can only be used once for `verifyEmailRegTicket`. Cannot retry with the same code. |
| 6 | STS redirect to invite API (400) | The STS redirects to `/api/v1/invitation/bind?userId=...` via GET, which returns 400 (POST-only endpoint). The serviceToken IS accepted (not 401), confirming it's valid for that redirect context. |

## Scripts

- `/root/mimo_browserless.py` — Steps 1-5 (register → verify → passToken → STS → invite API). Step 6 unresolved.
- `/root/mimo_final_flow.py` — Same as above but with file-based code waiting pattern (`/tmp/mimo_code.txt` + `/tmp/mimo_status.txt`). Includes 5 cookie delivery methods (A-E) for Step 6.
- `/root/mimo_ref_flow.py` — **NEW**: Tests `?ref=QB3238` URL parameter approach. Includes 6 methods: GET with ref param, session cookies, POST invite API, alternative endpoints, and invite redirect follow.

## Next Steps

1. **Test `?ref=` approach**: After STS flow (Steps 1-5), GET `https://platform.xiaomimimo.com?ref=QB3238` with serviceToken cookie. The `ref` parameter may trigger server-side referral binding.
2. **Capture raw Set-Cookie header**: Print `r.headers.get('Set-Cookie')` in the STS step to see Domain/Path/Secure/SameSite attributes. This is critical for understanding why serviceToken doesn't work with subsequent POST requests.
3. **Try Playwright with `?ref=` URL**: Navigate to `https://platform.xiaomimimo.com?ref=QB3238` after browser login. The SPA may handle the referral binding via JavaScript.

## Common Failures

| Issue | Cause | Fix |
|-------|-------|-----|
| userSynced returns no passToken | Fresh session without verify context | Must verify first in same session |
| STS returns 401 | Hardcoded/expired sign | Use loginUrl from 401 response |
| STS returns 401 (after modifying loginUrl) | Followup URL changed, breaking sign | NEVER modify the loginUrl |
| Invite API returns 401 | serviceToken not accepted | **UNRESOLVED** — see mystery above |
| verifyEmailRegTicket returns 70014 | Code expired or wrong | Get fresh code from user |
| serviceLoginAuth2 returns 70016 | Account needs browser verification | Use verifyEmailRegTicket instead |

## Working Script

`/root/mimo_browserless.py` implements Steps 1-4 (Step 5 unresolved):
```bash
# Step 1: Register
python3 mimo_browserless.py -e "email@routermail.biz.id"

# Step 2: Verify + Login + Apply (ONE session)
python3 mimo_browserless.py -e "email@routermail.biz.id" -v "CODE" -r "QB3238"
```
