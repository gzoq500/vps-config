---
name: tempmail-enterprise
description: "Deploy TempMail Enterprise — enterprise-grade temporary email service with C++ backend, Next.js frontend, Caddy HTTPS, Postfix/Dovecot mail, Brevo SMTP relay. Auto-expiring aliases, Indonesian names, API-first."
triggers:
  - tempmail
  - temp mail
  - temporary email
  - disposable email
  - email sementara
  - email alias generator
---

# TempMail Enterprise — Full Stack Setup

Enterprise-grade temporary email service. C++ backend (~0.1ms response), Next.js frontend, Caddy auto-HTTPS, Postfix receive, Dovecot IMAP, Brevo SMTP relay for sending.

Source: https://github.com/gzoq500/tempmail-enterprise

## Architecture

```
User → Caddy (:80/:443) → Next.js Frontend (:3002)
                        → C++ Backend API (:3001)
Postfix (:25) → pipe handler → Backend /api/incoming
Dovecot (:143/:993) → mailbox storage
Brevo SMTP relay (:587) → outbound email
```

## Install Steps

### 1. Dependencies

```bash
apt update && apt install -y cmake g++ git libsqlite3-dev pkg-config libssl-dev \
  postfix postfix-pgsql dovecot-imapd mailutils swaks sqlite3 \
  php-fpm php-sqlite3 php-mbstring php-xml php-zip php-gd php-curl
```

**Pitfall:** `dovecot-core` alone does NOT install the IMAP binary (`/usr/lib/dovecot/imap`). Must install `dovecot-imapd` separately.

### 2. Caddy (binary install)

```bash
curl -sL "https://github.com/caddyserver/caddy/releases/download/v2.8.4/caddy_2.8.4_linux_amd64.tar.gz" -o /tmp/caddy.tar.gz
tar -xzf /tmp/caddy.tar.gz -C /usr/local/bin/ caddy
chmod +x /usr/local/bin/caddy
```

Create systemd unit at `/etc/systemd/system/caddy.service`:

```ini
[Unit]
Description=Caddy
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/caddy run --config /etc/caddy/Caddyfile
ExecReload=/usr/local/bin/caddy reload --config /etc/caddy/Caddyfile
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### 3. Clone & Build

```bash
git clone https://github.com/gzoq500/tempmail-enterprise.git /opt/tempmail
cd /opt/tempmail/backend && mkdir -p build && cd build
cmake .. && make -j$(nproc)
# Verify: ls -la tempmail-server

cd /opt/tempmail/frontend
npm install && npm run build
```

### 4. Systemd Services

Backend (`/etc/systemd/system/tempmail-backend.service`):

```ini
[Unit]
Description=TempMail C++ Backend Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/tempmail/backend
ExecStart=/opt/tempmail/backend/build/tempmail-server --port 3001 --domain YOURDOMAIN
Restart=always
RestartSec=3
Environment=TEMPMAIL_PORT=3001
Environment=TEMPMAIL_DOMAIN=YOURDOMAIN
Environment=TEMPMAIL_DB=/opt/tempmail/backend/data/tempmail.db

[Install]
WantedBy=multi-user.target
```

Frontend (`/etc/systemd/system/tempmail-frontend.service`):

```ini
[Unit]
Description=TempMail Next.js Frontend
After=network.target tempmail-backend.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/tempmail/frontend
ExecStart=/usr/local/bin/node /opt/tempmail/frontend/node_modules/.bin/next start -p 3002
Restart=always
RestartSec=3
Environment=NODE_ENV=production
Environment=PORT=3002

[Install]
WantedBy=multi-user.target
```

### 5. Postfix — Email Handler

The email handler script pipes incoming mail to the backend API.

**Critical:** Postfix rejects `user=root` in pipe transport. Use `user=nobody` for basic delivery (API only). If using **dual delivery** (TempMail API + Roundcube mailbox), use `user=admin` because `/var/mail/admin` is owned by `admin:mail` and `nobody` gets "Permission denied". See pitfall #19.

`/etc/postfix/master.cf` — append:

```
tempmail unix - n n - 10 pipe
  flags=Rq user=nobody argv=/usr/local/bin/tempmail-handler ${sender} ${recipient}
```

Handler script at `/usr/local/bin/tempmail-handler` — extracts From/To/Subject/Body, POSTs to `http://localhost:3001/api/incoming`.

### 6. Caddyfile

```
tempmail.YOURDOMAIN {
    reverse_proxy /api/* localhost:3001
    reverse_proxy localhost:3002
}

mail.YOURDOMAIN {
    root * /var/lib/roundcube
    php_fastcgi unix//run/php/php8.1-fpm.sock
    file_server
}
```

Caddy auto-obtains Let's Encrypt certs when domain DNS points to server IP (DNS only mode, not proxied through Cloudflare for cert validation).

### 7. Postfix SMTP Config

```bash
# /etc/postfix/main.cf (key settings)
myhostname = mail.YOURDOMAIN
mydomain = YOURDOMAIN
mydestination = $myhostname, localhost.$mydomain, localhost, $mydomain
transport_maps = hash:/etc/postfix/transport
local_recipient_maps =
```

Transport: `echo "YOURDOMAIN tempmail:" > /etc/postfix/transport && postmap /etc/postfix/transport`

### 8. Brevo SMTP Relay (outbound)

```bash
cat > /etc/postfix/sasl_passwd << 'EOF'
[smtp-relay.brevo.com]:587 LOGIN:API_KEY
EOF
chmod 600 /etc/postfix/sasl_passwd
postmap /etc/postfix/sasl_passwd
```

Add to main.cf:
```
relayhost = [smtp-relay.brevo.com]:587
smtp_sasl_auth_enable = yes
smtp_sasl_security_options = noanonymous
smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd
smtp_tls_security_level = encrypt
```

### 9. Roundcube (Webmail)

```bash
DEBIAN_FRONTEND=noninteractive apt install -y roundcube roundcube-core roundcube-plugins
```

**Pitfall:** Roundcube defaults to MySQL. Reconfigure to SQLite:

```php
// /etc/roundcube/debian-db-roundcube.php
<?php
$dbtype = 'sqlite3';
$dbname = '/var/lib/roundcube/roundcube.db';
```

```bash
sqlite3 /var/lib/roundcube/roundcube.db < /usr/share/roundcube/SQL/sqlite.initial.sql
chown www-data:www-data /var/lib/roundcube/roundcube.db
```

Create login user: `useradd -m -s /bin/bash admin && echo 'admin:PASSWORD' | chpasswd`

### 10. DNS Records

| Type | Name | Content |
|------|------|---------|
| A | tempmail | SERVER_IP |
| A | mail | SERVER_IP |
| MX | @ | mail.YOURDOMAIN |
| TXT | @ | v=spf1 include:_spf.mailersend.net ~all |

## Custom Aliases (Beep/Beeb)

Stock backend only generates random names. Patch `backend/src/server.cpp` to accept `{"email":"custom@domain"}` in the POST body:

```cpp
// At the top of POST /api/alias handler, before the random loop:
std::string custom_email;
if (!req.body.empty()) {
    try {
        auto j = json::parse(req.body);
        if (j.contains("email")) custom_email = j["email"].get<std::string>();
    } catch (...) {}
}
if (!custom_email.empty()) {
    if (custom_email.find("@") == std::string::npos)
        custom_email += "@" + domain_;
    if (db_.get_alias(custom_email).has_value()) {
        res.status = 409;
        res.set_content(R"({"error":"Alias already exists"})", "application/json");
        return;
    }
    // ... same expiry/create logic as random path
}
```

After patching: `cd /opt/tempmail/backend/build && cmake .. && make -j$(nproc) && systemctl restart tempmail-backend`

Test: `curl -X POST http://localhost:3001/api/alias -H "Content-Type: application/json" -d '{"email":"golem@domain"}'`

## Dual Delivery (TempMail + Roundcube)

To make aliases appear in both TempMail UI AND Roundcube, modify `/usr/local/bin/tempmail-handler` to:
1. POST to TempMail API (existing)
2. Append to admin's mbox: `{ echo "From $FROM ..."; echo "$INPUT"; echo ""; } >> /var/mail/admin`

**Critical:** Postfix pipe must use `user=admin` (not `user=nobody`) to write to `/var/mail/admin`. See pitfall #19.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/health | Health check |
| POST | /api/alias | Generate random OR custom alias (`{"email":"..."}`) |
| GET | /api/aliases | List all aliases |
| GET | /api/emails/:address | Get emails for alias |
| POST | /api/incoming | Receive email from Postfix |
| POST | /api/send | Send email via SMTP |
| DELETE | /api/alias/:address | Delete alias |

### Backend: strip_html_tags() — Store clean text in body_text (July 2026)

Stock backend stores raw MIME in `body_text`. Add `strip_html_tags()` to `email_parser.cpp`:

```cpp
std::string strip_html_tags(const std::string& html) {
    std::string result = strip_style_blocks(html);  // removes <style>, <script>, <head>, comments
    // Convert block elements to newlines
    result = std::regex_replace(result, std::regex("<br\\s*/?>", std::regex::icase), "\n");
    result = std::regex_replace(result, std::regex("</p>", std::regex::icase), "\n\n");
    result = std::regex_replace(result, std::regex("</div>", std::regex::icase), "\n");
    result = std::regex_replace(result, std::regex("<tr[^>]*>", std::regex::icase), "\n");
    // Strip all remaining tags
    result = std::regex_replace(result, std::regex("<[^>]*>"), "");
    // Decode entities
    replace_all(result, "&amp;", "&"); replace_all(result, "&lt;", "<");
    replace_all(result, "&gt;", ">"); replace_all(result, "&nbsp;", " ");
    // Clean whitespace
    result = std::regex_replace(result, std::regex("[ \\t]{2,}"), " ");
    result = std::regex_replace(result, std::regex("\\n{3,}"), "\n\n");
    return trim(result);
}
```

In `server.cpp`, apply BEFORE `store_email()`:
```cpp
clean_body = strip_html_tags(clean_body);
if (clean_html.find("<") != std::string::npos) {
    std::string stripped = strip_html_tags(clean_html);
    if (stripped.length() > clean_body.length()) clean_body = stripped;
}
int id = db_.store_email(alias->id, from, to, subject, clean_body, clean_html);
```

**Key:** `body_html` keeps original HTML (for potential future rendering). `body_text` stores clean readable text.

### Backend: Handle old emails with raw HTML in body_text

Old emails (pre-fix) have raw HTML stored in `body_text`. Frontend must detect:
```typescript
const hasHtml = text.includes('<') && (text.includes('<html') || text.includes('<body') || text.includes('<!DOCTYPE'));
if (hasHtml) { /* strip HTML from body_text */ }
```

### Backend Fix (email_parser.cpp + server.cpp)
1. Add `base64_decode()`, `quoted_printable_decode()`, `decode_content()` to `email_parser.cpp`
2. Update `extract_html_body()` / `extract_text_body()` to capture MIME headers + route through decoder
3. Fix boundary regex: `[0-9a-f]+` → `[0-9a-zA-Z_+=/-]+`
4. In server.cpp: apply `quoted_printable_decode()` ONCE before `store_email()`. **NEVER decode twice** — corrupts `=abc` sequences

### Email Handler v3 (send raw body)
v2 handler used `sed` + `tr` which broke complex HTML. v3 sends full raw MIME body:
```bash
RAW_BODY=$(echo "$INPUT" | sed '1,/^$/d')
BODY_ESCAPED=$(echo "$RAW_BODY" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read())[1:-1])")
curl -s -X POST http://localhost:3001/api/incoming \
  -H "Content-Type: application/json" \
  -d "{\"from\":\"$FROM\",\"to\":\"$TO_EMAIL\",\"subject\":\"$SUBJECT\",\"body\":\"$BODY_ESCAPED\",\"html\":\"\"}"
```

### Frontend Fix (page.tsx) — PROVEN WORKING APPROACH (July 2026)
The most reliable approach: **strip ALL HTML, render as clean text with clickable URLs**.

```tsx
// In EmailDetail component, replace dangerouslySetInnerHTML with:
const text = email.body_text || '';
const hasHtml = text.includes('<') && (text.includes('<html') || text.includes('<body') || text.includes('<!DOCTYPE'));
let clean = text;
if (hasHtml) {
  // Old email: body_text contains raw HTML from pre-fix era
  clean = text
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<head>[\s\S]*?<\/head>/gi, '')
    .replace(/<br\s*\//gi, '\n').replace(/<\/p>/gi, '\n\n')
    .replace(/<\/div>/gi, '\n').replace(/<tr[^>]*>/gi, '\n')
    .replace(/<[^>]*>/g, '')
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&nbsp;/g, ' ')
    .replace(/=\r?\n/g, '').replace(/[\t]{2,}/g, ' ').replace(/\r/g, '')
    .replace(/\n{3,}/g, '\n\n').trim();
}
// Then linkifyText() for clickable URLs
```

**Why NOT use dangerouslySetInnerHTML with complex HTML:**
- Email tables (`<table bgcolor="#FFF">`) collapse to 0px height in `display:block` containers
- `<style>` tags with `<!--[if` CSS syntax break entire style blocks
- `mso-hide:all` hides buttons
- Conditional comments `<!--[if mso]>` hide content from modern browsers
- Backend `strip_html_tags()` + frontend `body_text` rendering = most reliable

**Alternative: iframe approach** (like Gmail):
```tsx
return <iframe srcDoc={`<html><body>${html}</body></html>`} 
  style={{width:'100%',minHeight:'400px',border:'none'}} />;
```
But iframe has issues with height calculation and link clicking.

### Backend Fix (server.cpp)
- Strip `mso-hide:all` from inline styles before storing
- Override `height:17px` → `height:auto`
- Apply `quoted_printable_decode()` ONCE before `store_email()` — NEVER decode twice

### Email Box UI (2x2 Grid)
Replace old card + action buttons: header with email address, 4-button grid (Change, Copy, Delete, Refresh), dark theme.

### Change Email Modal
Input username + domain + Random/Apply buttons. POST `/api/alias` with custom or random email.

## Pitfalls

1. **Postfix pipe `user=root` rejected.** Must use `user=nobody` in master.cf pipe transport.
2. **`dovecot-core` missing IMAP binary.** Install `dovecot-imapd` separately — `/usr/lib/dovecot/imap` not found otherwise.
3. **Dovecot duplicate config lines.** Appending `protocols = imap` to dovecot.conf when it already exists in a comment causes "starting up without any protocols". Use `doveconf -n` to check active config first.
4. **Caddy vs Apache port conflict.** Roundcube pulls in Apache. Stop/disable apache2 immediately: `systemctl disable --now apache2`.
5. **Roundcube needs MySQL by default.** Reconfigure to SQLite — much simpler, no MySQL/MariaDB dependency.
6. **SQLite3 CLI not always installed.** `apt install sqlite3` needed for DB initialization.
7. **Caddy auto-TLS needs port 80 open.** Let's Encrypt HTTP-01 challenge requires external access to port 80. Firewall must allow it.
8. **Cloudflare proxy blocks cert validation.** Set DNS records to "DNS only" (not proxied) for Caddy auto-TLS to work.
9. **PHP-FPM socket path.** Ubuntu22.04 uses `/run/php/php8.1-fpm.sock`. Check with `ls /run/php/php*.sock`.
10. **Aliases expire after24 hours.** By design — no manual cleanup needed.
11. **`postmap` warning on numeric hostname.** Don't use IP as `myhostname` — use `mail.YOURDOMAIN`.
12. **Email handler extra lines.** The repo's email-handler.sh may have trailing lines from heredoc. Clean with `head -41` before installing.
13. **Roundcube SQLite path doubling.** `sqlite:///var/lib/roundcube/roundcube.db` gets prepended with Roundcube's `APPLICATION_PATH` → `/var/lib/roundcube/var/lib/roundcube/roundcube.db` → file not found. **Fix:** move DB outside Roundcube's tree: `sqlite:////var/lib/roundcube-data/roundcube.db` (4 slashes = absolute path). Create dir + copy DB: `mkdir -p /var/lib/roundcube-data && cp /var/lib/roundcube/roundcube.db /var/lib/roundcube-data/ && chown www-data:www-data /var/lib/roundcube-data/roundcube.db`.
14. **Dovecot SSL cert CN mismatch.** Default self-signed cert has `CN=localhost.localdomain`. Roundcube expects `CN=localhost` → TLS handshake fails: `Peer certificate CN did not match expected CN`. **Fix:** generate cert with `openssl req -new -x509 -nodes -out /etc/dovecot/private/dovecot.pem -keyout /etc/dovecot/private/dovecot.key -subj "/CN=localhost"`. Also disable cert verification in Roundcube config: `$config['imap_conn_options'] = ['ssl' => ['verify_peer' => false, 'verify_peer_name' => false]];`.
15. **Roundcube IMAP user format.** Dovecot PAM auth expects bare username (`admin`), not email (`admin@domain`). Login with just `admin`, not `admin@routerssh.web.id`.
16. **Port conflict: Caddy + Apache.** Both Roundcube and Caddy want port 80. Roundcube apt install may pull Apache. Immediately `systemctl disable --now apache2` before starting Caddy.
17. **Postfix `user=root` not allowed.** Even though handler runs as root on the host, Postfix pipe transport rejects `user=root`. Must use `user=nobody`. Also ensure handler script is `chmod +x`.
18. **Brevo port.** Brevo SMTP relay uses port **587** (STARTTLS), not 2525. Main.cf needs `relayhost = [smtp-relay.brevo.com]:587`.
19. **Postfix pipe user for Roundcube mailbox.** If using dual delivery (TempMail API + Roundcube), the pipe must run as `user=admin` (not `user=nobody`) because `/var/mail/admin` is owned by `admin:mail`. With `user=nobody`, the append fails silently with "Permission denied". Update master.cf: `flags=Rq user=admin argv=/usr/local/bin/tempmail-handler`.
20. **Roundcube config key for TLS skip.** When Dovecot cert CN doesn't match, add to `/etc/roundcube/config.inc.php`:
    ```php
    $config['imap_conn_options'] = ['ssl' => ['verify_peer' => false, 'verify_peer_name' => false]];
    ```
21. **Roundcube `default_host` format.** Use `tls://localhost` (STARTTLS on 143), not `ssl://localhost` (implicit TLS on 993), unless you've confirmed the cert chain. STARTTLS is more forgiving with self-signed certs.
22. **Cloud providers (Tencent, AWS, GCP) may block inbound port 25.** External emails from Gmail/outlook never reach Postfix even though `ss -tlnp` shows port 25 listening. Connections from external IPs disconnect before SMTP handshake. **Workaround:** Use Cloudflare Email Routing (free) — dashboard Cloudflare → domain → Email → Email Routing → Enable → catch-all to server. Cloudflare receives email and forwards it, bypassing direct port 25. DNS records must be "DNS only" (not proxied) for MX. Also configure Postfix to listen on port 587 (submission) as backup inbound: add `submission inet n - y - - smtpd` to master.cf.
23. **Custom alias C++ patch.** Stock backend only generates random aliases. Patch `backend/src/server.cpp` to accept `{"email":"custom@domain"}` in POST body. See the skill's "Custom Aliases" section for the exact code. After patching: `cd /opt/tempmail/backend/build && cmake .. && make -j$(nproc) && systemctl restart tempmail-backend`.

24. **Postfix pipe `flags=Rq` causes `fatal: invalid option: R`.** On some Postfix versions (tested on 3.6.4 Ubuntu 22.04), the `R` flag in `flags=Rq` is not supported and causes the pipe to fail silently — emails get stuck in queue with no delivery logs. **Fix:** Use `flags=q` instead. This was observed when emails appeared in queue (`mailq`) but never reached the handler or mailbox, and `journalctl -u postfix` showed `fatal: invalid option: R`.

25. **Postfix queue stuck — "mail system is down" on flush.** After config changes or pipe errors, Postfix master process can enter a broken state where `postqueue -f` says "Cannot flush mail queue - mail system is down" even though `ss -tlnp` shows port 25 listening and `systemctl` says active. **Fix:** Force-kill and restart: `postfix stop; sleep 2; killall -9 master; sleep 1; postfix start`. Normal `systemctl restart postfix` may not kill the stuck master process. Also clear stuck messages with `postsuper -d ALL` before restarting.

26. **Postfix `mydestination` must include domain for local sendmail delivery.** When using `sendmail alias@domain` from the server itself, Postfix treats the domain as local (not relay). If the domain is NOT in `mydestination`, sendmail bounces with "User unknown". The working config has domain in BOTH `mydestination` AND `transport_maps` — transport_maps overrides local delivery for pipe routing.

35. **Caddy auto-upgrades to HTTPS breaks Cloudflare Worker fetch.** When adding `direct.domain` to Caddyfile without the `http://` prefix, Caddy auto-obtains a Let's Encrypt cert and redirects HTTP→HTTPS with a 308. Cloudflare Workers fetch the HTTP URL, get the 308 redirect, and the POST body is lost. **Fix:** Use `http://direct.domain` (with explicit `http://` prefix) in the Caddyfile so Caddy serves plain HTTP on port80 without redirecting. Example: `http://direct.routerssh.web.id { reverse_proxy /api/* localhost:3001 }`. Without the prefix, Caddy treats it as HTTPS-enabled and the Worker's POST to `http://direct.domain/api/incoming` gets a 308 redirect that drops the body.

36. **Cloudflare Worker fetch restrictions.** Workers cannot: (a) fetch to non-standard ports like `:3001` — must use port80/443; (b) fetch plain HTTP URLs — must use HTTPS; (c) fetch to domains proxied by the same Cloudflare account — creates a loop that silently fails. **Solution:** Create a DNS-only A record (`direct.domain → IP`, proxied=False) and have Caddy serve it on port80 with `http://` prefix. Worker fetches `https://direct.domain/api/incoming`.

37. **SPF record coexistence with Cloudflare Email Routing + Brevo.** When both Cloudflare Email Routing and Brevo are active, the SPF TXT record must include BOTH: `v=spf1 include:_spf.mx.cloudflare.net include:_spf.mailersend.net ~all`. Cloudflare may overwrite the SPF record when enabling Email Routing — manually edit to add both includes after enabling.

27. **Brevo inbound webhook requires enterprise plan.** Brevo's "Inbound webhooks" feature (under Plugins & Integrations → Webhooks → Inbound webhook) is only available on enterprise plan. The Brevo Transactional email page shows outbound settings (SMTP, Webhook for events, etc.) but NOT inbound email receiving. For inbound email, use Cloudflare Email Routing or direct MX to server.

28. **Cloudflare Email Routing conflict with existing MX.** If Cloudflare shows "Existing, non-Cloudflare MX records conflict with Email Routing", delete the old MX record first (e.g., `mail.domain → SERVER_IP` priority 10), then click "Add missing records" to let Cloudflare add its own MX records (route1/2/3.mx.cloudflare.net). Add destination address (e.g., Gmail), enable catch-all rule.

29. **API `/api/incoming` must also write to mbox for Roundcube.** The stock C++ backend only stores emails in SQLite via the API. When Cloudflare Worker posts to `/api/incoming`, emails appear in TempMail UI but NOT in Roundcube. **Fix:** Patch `server.cpp`'s POST `/api/incoming` handler to also append to `/var/mail/admin` in mbox format after `db_.store_email()`:
    ```cpp
    std::string mbox = "/var/mail/admin";
    FILE* f = fopen(mbox.c_str(), "a");
    if (f) {
        time_t now = time(nullptr);
        struct tm* t = gmtime(&now);
        char datebuf[64];
        strftime(datebuf, sizeof(datebuf), "%a %b %d %H:%M:%S %Y", t);
        fprintf(f, "From %s %s\n", from.c_str(), datebuf);
        fprintf(f, "From: %s\nFrom: %s\nTo: %s\nSubject: %s\n", from.c_str(), from.c_str(), to.c_str(), subject.c_str());
        fprintf(f, "Content-Type: text/plain; charset=UTF-8\n\n%s\n\n", body.c_str());
        fclose(f);
    }
    ```
    After patching: rebuild and restart backend.

30. **Cloudflare Worker for Email Routing → TempMail API.** Since port 25 is blocked by VPS providers, use a Cloudflare Worker to bridge Email Routing to the TempMail API. Deploy a Worker with the `email` handler that POSTs to `https://tempmail.domain/api/incoming`. Then change the Catch-all rule from "Send to email" to "Send to Worker". See `references/cloudflare-email-worker.js`.

31. **Cloudflare catch-all wildcard.** The email pattern field does NOT accept `*` — it says "Allowed characters: a-z 0-9 _ - . +". Use the dedicated **Catch-all address** option instead (separate from custom routing rules). Catch-all is configured at the bottom of the Routing Rules tab.

32. **SPF record coexistence with Cloudflare Email Routing.** When enabling Cloudflare Email Routing alongside Brevo, the SPF TXT record must include BOTH: `v=spf1 include:_spf.mx.cloudflare.net include:_spf.mailersend.net ~all`. Cloudflare may overwrite the SPF record — manually edit to add both includes.

34. **Cloudflare Worker MUST forward FULL email body — never truncate.** Using `raw.substring(idx+4, idx+504)` truncates to 500 chars, losing verification codes, OTP links, and email content. **Fix:** Use `raw.substring(idx+4)` (no end index) for full body. This was discovered when Xiaomi verification emails arrived with6124 bytes but the code portion was in the truncated section. Always forward the complete raw body.

38. **C++ email parser must decode base64/quoted-printable MIME content.** The stock `email_parser.cpp` extracts HTML/text body parts but does NOT decode `Content-Transfer-Encoding: base64` or `quoted-printable`. Magic links, verification URLs, and any encoded content appear as garbled raw base64 text (e.g., `aHR0cHM6Ly9...`). **Fix:** Add `base64_decode()` and `quoted_printable_decode()` functions to `email_parser.cpp`, then modify `extract_html_body()` and `extract_text_body()` to capture the MIME part headers (including Content-Transfer-Encoding) and pass them through `decode_content()` before returning. Also fix the MIME boundary regex from `[0-9a-f]+` to `[0-9a-zA-Z_+=/-]+` — real boundaries contain uppercase, dashes, and equals signs.

39. **Frontend text body must NOT strip HTML tags from plain text.** The stock `page.tsx` EmailDetail component uses `.replace(/<[^>]*>/g, '')` on `body_text`, which destroys URLs that contain angle brackets and removes any HTML-like content. **Fix:** Replace the regex strip with a URL auto-linker: split text on `(https?:\/\/[^\s<>"']+)` and render URL parts as clickable `<a>` tags with `target="_blank"`. Keep `whiteSpace: 'pre-wrap'` and add `overflowWrap: 'break-word'` for long URLs.

40. **QP decoder must ONLY match uppercase hex (A-F) to prevent data corruption.** The `quoted_printable_decode()` function matches `=XX` where XX are hex digits. If lowercase hex (a-f) is accepted, decoded content like `=edge` (from `=3Dedge`) gets re-decoded as `=ed` → 0xED → invalid UTF-8 byte. This corrupts HTML attributes (e.g., `content="IE=edge"` becomes `content="IE�ge"`), crashes JSON serialization in C++ (HTTP 500), and crashes Python sqlite3 with `OperationalError: Could not decode to UTF-8`. **Fix:** Only match uppercase hex: `(h1>='A'&&h1<='F')` not `(h1>='a'&&h1<='f')`. Standard QP encoding always uses uppercase. Also add UTF-8 sanitization when reading corrupted data from DB: `conn.text_factory = bytes` + `.decode('utf-8', errors='replace')`.

41. **Backend MUST strip `mso-hide:all` from inline styles before storing.** Outlook-specific `mso-hide:all` CSS property hides elements from non-Outlook clients. Buttons like "Confirm Email" in Gologin emails have this inline style, making them invisible in the web UI. **Fix:** In `server.cpp`, after `quoted_printable_decode()`, strip all `mso-hide` occurrences with a while loop. Also override `height: 17px` → `height: auto` for button visibility.

45. **Root cause of blank email body: invalid CSS `<!--[if` in emailStyles.** The `emailStyles` template literal in `page.tsx` contained `.email-html-content <!--[if { display: none !important; }` — the `<!--[if` is NOT valid CSS and breaks the ENTIRE `<style>` tag, preventing ALL email content from rendering. This causes the white card to appear empty. **Fix:** Remove the `<!--[if` selector entirely. Replace with `.email-html-content noscript, .email-html-content xml { display: none !important; }`. Always verify emailStyles has valid CSS syntax after editing.

46. **Table elements collapse to zero height in `display: block` containers.** Email HTML from services like Capsolver uses `<table>` with `bgcolor="#FFF"` and `style="height: 100%"`. When rendered inside a React `<div>` with `overflow: hidden`, the table collapses to 0px height because: (a) `display: block` div with tables requires explicit sizing, (b) `height: 100%` on table means 0px if parent has no explicit height. **Fix:** Add CSS overrides: `.email-html-content table { display: table !important; width: 100% !important; height: auto !important; }` and `.email-html-content tbody, .email-html-content tr, .email-html-content td { display: revert !important; }`. Also remove ALL light background colors from HTML: `background-color: #FFF`, `#F2F4F6`, `#FAF9F5`, `#F5F5F5`, `#F8F9FA`. Use regex: `background-color:\s*#(?:fff|ffffff|faf9f5|f5f5f5|f2f4f6|f8f9fa|f0f0f0)[^;]*;?`.

47. **Backend `clean_mime_body()` must be called BEFORE `store_email()`, not after.** The stock code stores raw MIME content directly. The fix applies `clean_mime_body()` + `quoted_printable_decode()` + `mso-hide` stripping BEFORE the INSERT. This ensures all emails in the DB have clean HTML.

48. **Frontend rendering strategy: strip HTML for reliability.** For maximum compatibility across all email clients, strip ALL HTML tags and render as plain text with clickable URLs. This avoids table collapse, conditional comment, and CSS issues entirely. Use: `raw.replace(/<br\\s*\\//gi, '\\n').replace(/<\\/p>/gi, '\\n\\n').replace(/<tr[^>]*>/gi, '\\n').replace(/<[^>]*>/g, '').replace(/&amp;/g, '&')...` then `linkifyText()` for URLs.

49. **Backend MUST preserve links before stripping HTML tags.** The `strip_html_tags()` function removes ALL `<a>` tags, losing verification/confirmation URLs. **Fix:** Convert `<a href="URL">text</a>` to `text [URL]` BEFORE the generic tag strip. C++ regex: `std::regex link_re("<a[^>]*href=\\\"([^\\\"]*)\\\"[^>]*>([^<]*)</a>", std::regex::icase);` then `std::regex_replace(result, link_re, "$2 [$1]");`. **Pitfall:** Do NOT use `[\s\S]*?` for link text — C++ regex warns on `\S` (unknown escape). Use `[^<]*` instead. The frontend `linkifyText()` then converts `[URL]` to clickable `<a>` tags.

50. **Frontend body_text-first rendering (proven working).** When backend stores clean text in `body_text`, frontend should use it directly WITHOUT running `extractHtmlFromMime`. **Pattern:** `const text = email.body_text || ''; if (text.trim().length > 10) { const linked = linkifyText(text.replace(/\r/g, '').replace(/\n/g, '<br/>')); return <div ... dangerouslySetInnerHTML={{ __html: linked }} />; }`. For old emails where `body_text` still has raw HTML (pre-fix), detect with: `const hasHtml = text.includes('<') && (text.includes('<html') || text.includes('<body') || text.includes('<!DOCTYPE'));` and strip if true.

51. **Email body_text whitespace cleanup pipeline (order matters).** After HTML stripping, apply in this exact order: (1) `replace(/\r/g, '')` — remove carriage returns, (2) `replace(/[ \t]{2,}/g, ' ')` — collapse multiple spaces, (3) `replace(/\n[ \t]+/g, '\n')` — remove leading whitespace from lines, (4) `replace(/\n{3,}/g, '\n\n')` — collapse triple+ newlines, (5) `.trim()`. Wrong order produces messy output with scattered `\r` characters.

52. **C++ regex escaping pitfall.** C++ `std::regex` treats `\S` as unknown escape sequence (warning). Always use `[^<]*` instead of `[\s\S]*?` for matching link text or tag content. Similarly, `\s` works but `\S` does not in C++ regex character classes. For matching any char including newlines, use `[^]` or loop-based string processing instead of regex.

53. **mso-hide:all removal from backend.** Outlook-specific `mso-hide:all` inline CSS hides buttons from non-Outlook browsers. **Backend fix:** After `quoted_printable_decode()`, apply while loop: `while (clean_html.find("mso-hide") != std::string::npos) { auto pos = clean_html.find("mso-hide"); auto end = clean_html.find(";", pos); clean_html.erase(pos, end != npos ? end-pos+1 : clean_html.size()-pos); }`. Also override `height: 17px` → `height: auto` for button visibility.

54. **Always push fixes to GitHub after each successful change.** User preference: push to `gzoq500/tempmail-enterprise` immediately after each working fix, not batch at the end. This prevents losing work if something breaks later. Command: `cp /opt/tempmail/frontend/src/app/page.tsx /tmp/tempmail-enterprise/frontend/src/app/page.tsx && cd /tmp/tempmail-enterprise && git add -A && git commit -m "fix: description" && git push origin master`.

55. **Always backup before C++ patches.** C++ regex or logic errors cause crash (Internal Server Error 500). Always `cp /opt/tempmail/backend/src/email_parser.cpp /tmp/email_parser.cpp.bak` before editing. If crash occurs: `cp /tmp/email_parser.cpp.bak /opt/tempmail/backend/src/email_parser.cpp && cd /opt/tempmail/backend/build && make -j$(nproc) && systemctl restart tempmail-backend`.

42. **Frontend MUST strip `<!--[if !mso]>` comment DELIMITERS but KEEP content inside.** Modern browsers treat ALL `<!--[if ...]>` as HTML comments → content inside is invisible. The `<!--[if !mso]><!-->` block contains the actual clickable `<a>` button (the non-Outlook version). The `<!--[if mso]>` block contains VML (Outlook-only) — safe to remove entirely. **Fix in `extractHtmlFromMime`:** Remove `<!--[if mso]>...<![endif]-->` entirely. Strip only the delimiters of `<!--[if !mso]><!-->` and `<!--<![endif]-->` — keep everything between them. Also remove VML namespace tags (`<v:*>`, `<w:*>`) and add CSS override: `.email-html-content a[style*="background"] { display: inline-block !important; height: auto !important; min-height: 40px; }`.

43. **Email handler v3: send FULL raw MIME body to backend.** The v2 handler used `sed` + `tr '\n' ' '` to parse HTML from the raw email, which breaks complex HTML with conditional comments spanning multiple lines (e.g., Outlook-rendered emails with `<!--[if mso]>` blocks). **Fix:** v3 sends the entire raw body (after first blank line) as the `body` field, with `html=""`. The C++ backend's `clean_mime_body()` handles all extraction and decoding. Use `python3 -c "import sys,json; print(json.dumps(sys.stdin.read())[1:-1])"` for JSON-safe escaping of the raw body.

44. **UTF-8 sanitization for corrupted email content.** Emails stored before the QP fix may contain invalid UTF-8 bytes (0xED, 0x01, etc.) that crash both C++ JSON serializer (HTTP 500) and Python sqlite3 (`OperationalError: Could not decode to UTF-8`). **Fix:** Read DB with `conn.text_factory = bytes`, then `.decode('utf-8', errors='replace')`. Clean: `re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', html)`. Apply to all emails with `UPDATE emails SET body_html=?, body_text=? WHERE id=?`.

33. **API `/api/incoming` mbox write must happen BEFORE alias check.** The stock C++ backend's POST `/api/incoming` handler does: get alias → if no alias return early → store + mbox write. Emails to non-registered aliases like `test@domain` return `{"success":true,"message":"No matching alias"}` but never write to `/var/mail/admin`. When Cloudflare Worker forwards external emails to arbitrary addresses, most won't have registered aliases. **Fix:** Move the mbox write code block BEFORE the `db_.get_alias(to)` call so ALL incoming emails get written to the Roundcube mailbox regardless of alias existence. Rebuild after patching: `cd /opt/tempmail/backend/build && cmake .. && make -j$(nproc) && systemctl restart tempmail-backend`.

## Verified Stack (Ubuntu22.04)

| Component | Version | Port | RAM |
|-----------|---------|------|-----|
| C++ Backend | custom | 3001 | ~5MB |
| Next.js Frontend | 14.x | 3002 | ~100MB |
| Caddy | 2.8.4 | 80,443 | ~40MB |
| Postfix | 3.6.4 | 25 | minimal |
| Dovecot | 2.3.16 | 143,993 | minimal |
| PHP-FPM | 8.1 | socket | minimal |
| Roundcube | 1.5.0 | via Caddy | via PHP |
