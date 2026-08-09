# Session lessons 2026-07-22 (MiMo + migration + ops)

## User preferences reinforced
- Bahasa Indonesia, singkat, **langsung eksekusi**
- Kode verifikasi: tulis ke `/tmp/mimo_code.txt` **segera**
- Before each attempt: **clean processes + fresh residential IP + verify ipinfo**
- On failure: **analyze root cause**, don't blind-retry same stack
- Prefer **native 9Router** (no Docker) when asked
- Migration: **single tarball** with memory + scripts + keystores + units

## MiMo blocker
- Full UI+API path works through Redeem click
- Still **400909** under automation
- Manual browser OK → detection is automation fingerprint (`api-platform_ph`), not IP alone
- nodriver promising (`webdriver=False`) but UI path still hits INPUTS:0 / empty URL / None evaluate

## Operational
- 3.6GB VPS: avoid Chrome+Xvfb+Mysterium simultaneous
- routermail.biz.id may 88205-block
- Mysterium: unlock PUT original password; filter providers without access_policies; iterate providers on reject
- Handover pack: `kezem_vps_transfer.tar.gz` → VPS `45.130.164.191`

## Next experiments (priority)
1. Stabilize nodriver until 6 OTP inputs visible
2. Capture `api-platform_ph` from real browser vs auto
3. TLS client fingerprint for pure-API bind (if cookie domain allows)
4. Semi-manual redeem path as reliable fallback