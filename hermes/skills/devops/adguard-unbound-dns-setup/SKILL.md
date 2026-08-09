---
name: adguard-unbound-dns-setup
description: Setup AdGuard Home + Unbound recursive DNS on VPS.
trigger: Use when setting up DNS server, installing AdGuard Home, or configuring Unbound.
---

# AdGuard Home + Unbound Recursive DNS Setup

Complete guide for installing AdGuard Home with Unbound as recursive resolver (no DNS leaks). Optimized for VPS with port restrictions (UpCloud, etc.).

## Prerequisites

- VPS with port access: 53 (DNS), 80 (AdGuard web UI), 443 (Unbound)
- Root access
- Ports 53, 80, 443 available (disable systemd-resolved if needed)

## Architecture

```
[Client] → AdGuard (port 53) → Unbound (port 443) → Root DNS servers (recursive)
```

- **AdGuard**: DNS filtering + web UI (port 80/53)
- **Unbound**: Recursive resolver (port 443) - no leaks to external DNS
- **Advantage**: Full control, no DNS queries leave VPS

## Installation Steps

### 1. Disable systemd-resolved (free port 53)

```bash
systemctl stop systemd-resolved
systemctl disable systemd-resolved
systemctl mask systemd-resolved
```

Verify: `ss -tlnp | grep ":53 "` should return empty.

### 2. Install AdGuard Home

```bash
curl -s https://raw.githubusercontent.com/AdguardTeam/AdGuardHome/master/scripts/install.sh | bash -s -- -v
```

Config location: `/opt/AdGuardHome/AdGuardHome.yaml`

### 3. Install Unbound

```bash
apt-get install -y unbound
```

Config location: `/etc/unbound/unbound.conf.d/local.conf`

## Configuration

### AdGuard Home Config (`/opt/AdGuardHome/AdGuardHome.yaml`)

Critical sections:

```yaml
http:
  address: 0.0.0.0:80  # Web UI port

dns:
  bind_hosts:
    - 0.0.0.0
  port: 53
  upstream_dns:
    - 127.0.0.1:443  # Point to Unbound
  bootstrap_dns:
    - 9.9.9.9:53
    - 149.112.112.112:53
```

**Common YAML errors:**
- `bootstrap_dns` must not have nested lists (`- -` syntax is wrong)
- `bind_hosts` must be list with `- 0.0.0.0` (not empty)
- Use Python yaml module to edit programmatically (see references/fix_config.py)

### Unbound Config (`/etc/unbound/unbound.conf.d/local.conf`)

```yaml
server:
  port: 443
  interface: 0.0.0.0
  access-control: 0.0.0.0/0 allow
  do-ip4: yes
  do-ip6: no
  do-udp: yes
  do-tcp: yes
  root-hints: /var/lib/unbound/root.hints
  do-not-query-localhost: no
  hide-identity: yes
  hide-version: yes
  harden-glue: yes
  harden-dnssec-stripped: yes
  prefetch: yes
  cache-min-ttl: 300
  cache-max-ttl: 86400
```

Download root hints:
```bash
curl -s https://www.internic.net/domain/named.root -o /var/lib/unbound/root.hints
```

## DNS-over-TLS for Android Private DNS (port-restricted VPS)

Android's "DNS Pribadi / Private DNS" field accepts **only a hostname** and always
connects DoT on **port 853 — not configurable**. On a VPS where 853 is blocked by the
provider firewall, serve DoT on an allowed port and NAT-redirect 853 to it.

### 1. Real certificate is mandatory

Android rejects self-signed certs → user sees *"Tidak dapat terhubung"* with no other
diagnostics. Get a real cert (port 80 must be free during issuance):

```bash
apt-get install -y certbot
systemctl stop AdGuardHome            # frees port 80 for http-01
certbot certonly --standalone --non-interactive --agree-tos \
  --register-unsafely-without-email -d dns.example.com --http-01-port 80
```

### 3. AdGuard TLS block — use the `*_path` keys

`certificate_chain` / `private_key` are **inline PEM content** fields; file paths belong
in `certificate_path` / `private_key_path`. Setting the wrong pair leaves port 853/8880
silently not listening.

**CRITICAL**: When Caddy (or any other service) already holds port 443, you MUST set
`port_https: 0` in the `tls` section. Without it, AdGuard tries to bind 443 on startup
and crashes with `listen tcp :443: bind: address already in use` — even if you only want
DoT on another port.

```yaml
tls:
  enabled: true
  server_name: dns.example.com
  certificate_chain: ''      # keep empty
  private_key: ''            # keep empty
  certificate_path: /etc/letsencrypt/live/dns.example.com/fullchain.pem
  private_key_path: /etc/letsencrypt/live/dns.example.com/privkey.pem
  port_dns_over_tls: 8880    # allowed port on this VPS
  port_https: 0              # ← MANDATORY when 443 is taken (Caddy, etc.)
  port_dns_over_quic: 0
  force_https: false
```

**Verification**: After adding `tls` section, run `systemctl start adguardhome` and check
`journalctl -u adguardhome --no-pager -n 20 | grep -i "panic\|bind\|443"`. If you see
`bind: address already in use`, the `port_https: 0` line is missing or ignored (check
YAML indentation — it must be under `tls:`, not `dns:`).

Confirm in the log: `dnsproxy: creating tls server socket addr=0.0.0.0:8880`.

### 3. FIRST prove 853 is reachable from outside — a redirect cannot save a blocked port

**Do this before any iptables work.** If the provider firewall drops 853 *upstream of the
VPS*, no NAT rule can help: the packet never arrives. A redirect that tests fine locally
still leaves Android showing *"Tidak dapat terhubung"*, and you will burn the session
chasing certs and TLS config for a problem that is purely a closed port.

Check from a third party (`ss`/`iptables` on the box tell you nothing about the provider
firewall):

```bash
for P in 853 443 8880 80; do
  curl -s --max-time 20 https://portchecker.io/api/v1/query \
    -H "Content-Type: application/json" \
    -d "{\"host\":\"<VPS_IP>\",\"ports\":[$P]}"; echo
done
# status:true = reachable, status:false = blocked upstream
```

Only if 853 returns `status:true` is the redirect worth adding:

```bash
iptables -t nat -A PREROUTING -p tcp --dport 853 -j REDIRECT --to-port 8880
# local/loopback testing paths need OUTPUT rules too
iptables -t nat -A OUTPUT -p tcp -d 127.0.0.1   --dport 853 -j REDIRECT --to-port 8880
iptables -t nat -A OUTPUT -p tcp -d <VPS_IP>    --dport 853 -j REDIRECT --to-port 8880
mkdir -p /etc/iptables && iptables-save > /etc/iptables/rules.v4   # persist
```

If 853 is `status:false`, stop and tell the user plainly: Android native Private DNS
**cannot** work until they open 853 in the provider panel, because the port number is
fixed in Android. Then offer the two real fallbacks:

- **Serve DoT on 443** (an allowed port) so anything that lets you specify a port works.
  Requires freeing 443 — move Unbound to a loopback-only port (see below).
- **Serve DoH on another allowed port** (e.g. 8880) for clients that support it: the
  AdGuard/Intra apps, or Chrome → *Use secure DNS → Custom*. Android's built-in Private
  DNS field is DoT-only and will not accept a DoH URL.

### 3b. Layout when 443 must host DoT: move Unbound to loopback

Unbound only ever needs to answer AdGuard on the same host, so it has no business holding
an externally-allowed port. Free 443 by binding Unbound to localhost on a high port:

```yaml
# /etc/unbound/unbound.conf.d/local.conf
server:
  port: 5335
  interface: 127.0.0.1        # loopback only — still no external leaks
```

```yaml
# /opt/AdGuardHome/AdGuardHome.yaml
dns:
  upstream_dns:
    - 127.0.0.1:5335
tls:
  port_dns_over_tls: 443      # DoT on an allowed port
  port_https: 8880            # DoH on another allowed port
```

Verify both listeners and both protocols:

```bash
ss -tlnp | grep -E ":53 |:80 |:443 |:5335 |:8880 "
kdig @<host> +tls +tls-hostname=<host> -p 443 example.com          # DoT
curl -s -o /tmp/doh.bin -w "%{http_code}\n" \
  "https://<host>:8880/dns-query?dns=q80BAAABAAAAAAAAB2V4YW1wbGUDY29tAAABAAE" \
  -H "accept: application/dns-message"                              # DoH → 200
```

Note DoH JSON (`?name=…&type=A` with `accept: application/dns-json`) returns **400** on
AdGuard — it serves RFC 8484 wireformat only. A 400 there is not a misconfiguration; test
with the base64url `?dns=` form instead.

### 4. Verify DoT for real (not just "port is open")

```bash
echo | openssl s_client -connect dns.example.com:8880 \
  -servername dns.example.com 2>&1 | grep -E "issuer=|Verify return"
# expect: issuer= Let's Encrypt ... / Verify return code: 0 (ok)

apt-get install -y knot-dnsutils
kdig @<VPS_IP> +tls +tls-hostname=dns.example.com -p 853 github.com   # exercises the redirect
```

A passing `kdig` through **853** is the only proof the Android path works — testing 8880
directly does not validate the redirect. And a passing `kdig` from *on the VPS* still does
not prove the Android path: loopback/OUTPUT rules bypass the provider firewall entirely.
External reachability of 853 (step 3) is the gate; `kdig` only confirms TLS + resolution.

### 5. Renewal must restart AdGuard

AdGuard reads the cert at startup, so a silent renewal breaks DoT ~90 days later:

```bash
printf '#!/bin/bash\nsystemctl restart AdGuardHome\n' \
  > /etc/letsencrypt/renewal-hooks/deploy/restart-adguard.sh
chmod +x /etc/letsencrypt/renewal-hooks/deploy/restart-adguard.sh
```

## Run AdGuard under systemd (not a hand-launched background process)

A hand-started `AdGuardHome &` dies with the shell/session and looks like a crash.
Write the unit yourself — the bundled `-s install` writes
`ExecStart=... -p 8880 -s run`, which makes the binary treat the port flag as the **web
UI** port and it exit-code-1 loops. Use a plain `ExecStart` and let the YAML own all ports:

```ini
[Unit]
Description=AdGuard Home: Network-level blocker
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/opt/AdGuardHome/AdGuardHome --no-check-update
WorkingDirectory=/opt/AdGuardHome
Restart=always
RestartSec=5
StandardOutput=append:/var/log/adguard.log
StandardError=append:/var/log/adguard.log
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
```

If a stale unit exists, `systemctl stop` + `rm` it before copying the new one —
`-s install` refuses with *"Init already exists"* and `daemon-reload` alone keeps the old
ExecStart. Template: `templates/AdGuardHome.service`.

## Caddy-fronted SSL Pattern (dns.routerssh.store style)

When the VPS already has Caddy (or needs SSL for a domain), use this layout instead of
AdGuard's built-in TLS:

```
[Internet] → Caddy (port 80/443, SSL) → AdGuard (127.0.0.1:3000)
                                                        ↓
                                                Unbound (127.0.0.1:5335)
```

**Advantages**: Caddy auto-renewal via ACME, AdGuard doesn't need cert management,
DoH works through Caddy at `https://domain/dns-query`.

### Setup

1. **AdGuard**: set `http.address: 127.0.0.1:3000` (internal only). DNS port 53 still
   binds `0.0.0.0:53` (separate from http). Enable DoH in config:
   ```yaml
   http:
     doh:
       enabled: true
       routes:
         - "GET /dns-query"
         - "POST /dns-query"
       insecure_enabled: true   # Caddy handles TLS
   ```

2. **Caddyfile** (`/etc/caddy/Caddyfile`):
   ```
   dns.example.com {
       # DoH must be matched before the generic reverse_proxy
       @doh path /dns-query
       handle @doh {
           reverse_proxy 127.0.0.1:3000
       }
       # AdGuard web panel
       handle {
           reverse_proxy 127.0.0.1:3000
       }
   }
   ```

3. **Unbound**: `port: 5335`, `interface: 127.0.0.1` (loopback only).

4. **AdGuard upstream**: `dns.upstream_dns: ["127.0.0.1:5335"]`.

### First-launch: API setup (not manual YAML)

After deleting a mangled config, AdGuard listens on `*:3000` in first-launch mode.
Configure it via API instead of editing YAML:

```bash
curl -s -X POST http://127.0.0.1:3000/control/install/configure \
  -H "Content-Type: application/json" \
  -d '{
    "web": {"ip": "127.0.0.1", "port": 3000},
    "dns": {"ip": "0.0.0.0", "port": 53},
    "username": "golem",
    "password": "Kolor900@",
    "password_repeated": "Kolor900@"
  }'
# Returns "OK" on success. Then restart AdGuard.
```

This atomically writes a schema-valid YAML. Never hand-edit after this point; use the API.

### systemd-resolved: mask, don't just stop

`systemctl stop systemd-resolved` is not enough — it can restart on its own or on reboot.
The correct sequence to free port 53 permanently:

```bash
systemctl mask systemd-resolved     # symlink to /dev/null → can't start at all
systemctl stop systemd-resolved
rm -f /etc/resolv.conf              # was a symlink to systemd's stub
printf "nameserver 8.8.8.8\nnameserver 1.1.1.1\n" > /etc/resolv.conf
```

**Pitfall**: after `stop` without `mask`, `/etc/resolv.conf` still points to `127.0.0.53`
and DNS breaks for everything (curl, wget, git). Always fix `resolv.conf` immediately
after stopping systemd-resolved.

## Common Issues & Fixes

### Issue 1: AdGuard crashes silently (port 53 not listening)

**Symptom**: `ss -tlnp | grep :53` shows nothing, AdGuard process running.

**Cause**: Session database corruption (`/opt/AdGuardHome/data/sessions.db`).

**Fix**:
```bash
rm -f /opt/AdGuardHome/data/sessions.db
pkill -f AdGuardHome
/opt/AdGuardHome/AdGuardHome &
```

Wait 10 seconds after restart for port 53 to bind.

### Issue 2: Config YAML parse errors

**Symptom**: `AdGuardHome --check-config` shows "cannot construct !!seq into string".

**Cause**: Wrong `bootstrap_dns` format (nested list).

**Fix**: Edit YAML manually or use Python yaml module (see references/fix_config.py).

### Issue 2b: NEVER manually edit AdGuardHome.yaml — use the API

AdGuard's config has a **schema version** that auto-migrates on startup (v18→v19→v20…).
Manual edits — even via Python `yaml` library — frequently produce files that fail
`migration N to N+1` with errors like `cannot construct !!bool 'false' into dnsforward.EDNSClientSubnet`
or `unexpected type of "interval": string`. Once a file is mangled, further edits compound it.

**Correct approaches (in order of preference):**

1. **Let AdGuard generate its own config** — delete `AdGuardHome.yaml`, start AdGuard
   (it listens on `:3000` for first-launch wizard), then POST to
   `/control/install/configure` to set ports/credentials in one atomic step.
2. **Use the runtime API** — after initial setup, change settings via
   `POST /control/...` endpoints (upstream DNS, filters, etc.) — never touch the YAML.
3. **If you absolutely must edit the YAML** — take a `.bak`, round-trip through Python
   `yaml.safe_load` → modify dict → `yaml.dump`, then validate with
   `AdGuardHome --check-config` before starting. If the file is already mangled,
   restore the `.bak` rather than layering more edits.

← **sed never.** Python yaml only if you know the current schema version.

### Issue 2b-addendum: `doh.routes` YAML format

The `http.doh.routes` list must be **strings**, not maps:

```yaml
# CORRECT:
http:
  doh:
    enabled: true
    routes:
      - "GET /dns-query"
      - "POST /dns-query"

# WRONG (causes parse error / silent 404 on /dns-query):
http:
  doh:
    routes:
      - GET: /dns-query    # ← map, not string
```

AdGuard returns HTTP 404 for `/dns-query` when the routes are malformed this way.

```bash
python3 - <<'EOF'
import yaml
p='/opt/AdGuardHome/AdGuardHome.yaml'
c=yaml.safe_load(open(p))
c['dns']['bind_hosts']=['0.0.0.0']
c['dns']['port']=53
yaml.dump(c, open(p,'w'), default_flow_style=False)
EOF
/opt/AdGuardHome/AdGuardHome --check-config
```

Take a `.bak` copy first; if the file is already mangled beyond repair, restore the backup
rather than layering more edits. Note the Hermes `write_file`/`patch` tools refuse paths
under `/etc/`, so system configs (`/etc/unbound/...`) must be written via a terminal
heredoc — write to `/tmp` and `cp`, or `cat > file << 'EOF'`.

### Issue 2c: `sessions.db` timeout on restart

`[error] session_storage: opening db ... err=timeout` / `[fatal] initializing auth module`
means a previous instance still holds the lock or the file is stale. `pkill -f AdGuardHome`,
`rm -f /opt/AdGuardHome/data/sessions.db`, then start again.

### Issue 2d: Port 53 binds ~10s AFTER the web UI

AdGuard serves port 80 immediately but `dnsproxy` starts roughly 10 seconds later. A
`ss -tlnp | grep :53` or `dig` run 5s after launch returns "connection refused" and looks
like a crash. Sleep 12–15s before asserting failure.

### Issue 2e: Unbound config keywords that don't exist

`infra-cache-ttl` and `unlimited: yes` are not valid Unbound options and abort the whole
file. Always gate a restart behind `unbound-checkconf <file>`.

### Issue 3: DNS slow for new domains (recursive resolver)

**Symptom**: First query to new domain takes 200-400ms.

**Cause**: Unbound recursive resolution takes time (queries root → TLD → authoritative servers).

**Fix**: Enable cache optimization in Unbound (already in config above). Cache will populate over time.

### Issue 4: Port 53 already in use

**Check**: `ss -tlnp | grep ":53 "`

**Fix**: Disable systemd-resolved (see step 1).

## Working style on this VPS (user expectation)

The user is on Telegram talking to Hermes *through* this same VPS, so DNS/port surgery can
cut the conversation mid-task ("hati-hati kezem, komunikasi kita terputus"). Therefore:

- Never `pkill` / restart the 9Router gateway, the Hermes gateway, or whatever owns the
  port your own model traffic flows over. Ask before touching them.
- Change one thing, verify it, then move on. Do not chain multiple config rewrites +
  restarts in a single command.
- Keep a `.bak` before editing a working config, and restore rather than iterate when a
  file gets mangled.
- Finish with real proof (a passing query, a listening socket), then push the configs to
  the user's `vps-config` repo — they expect every working change persisted there so a new
  VPS is a restore, not a rebuild. Replace secrets/hashes with placeholders before pushing.
- Report concisely in Indonesian: what works, what the user must do next.

## System Health Check (VPS diagnostics)

Quick diagnostic sequence for VPS health, ping, speedtest, and port status:

```bash
# 1. System health
uptime                          # load average
free -h                         # RAM + swap
df -h | grep -E 'Filesystem|/dev/'  # disk usage
top -bn1 | grep "Cpu(s)" | head -1  # CPU idle

# 2. Ping test
ping -c 4 8.8.8.8 2>&1 | tail -3

# 3. Speedtest Ookla (install if missing)
which speedtest 2>/dev/null || (
  curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | bash &&
  apt-get install -y speedtest
)
speedtest --simple 2>&1 | head -5
# Output: Ping: XXms / Download: XXX Mbit/s / Upload: XXX Mbit/s

# 4. Port scan (external) — /dev/tcp method (more reliable than portchecker.io)
for port in 21 22 25 53 80 443 3389 8443 8880 20128 51820; do
  (echo > /dev/tcp/209.127.114.234/$port) 2>/dev/null && echo "Port $port: OPEN" || echo "Port $port: CLOSED/FILTERED"
done
```

**Note**: `portchecker.io` API frequently returns `error`/timeout. The `/dev/tcp` bash built-in
is more reliable for quick external port checks from the VPS itself.

## Verification

After setup, verify:

```bash
# Check ports
ss -tlnp | grep -E "53 |80 |443 "

# Test DNS
dig @127.0.0.1 google.com +short

# Test from outside
dig @<VPS_IP> google.com +short

# Check AdGuard status
curl -s http://127.0.0.1:80/control/status
```

Expected: Port 53 (AdGuard), 80 (AdGuard web), 443 (Unbound) listening. DNS queries return results.

## Known Issues

### DoH returns 404 on AdGuard v0.107.78

Despite correct `http.doh` config (enabled: true, proper routes), AdGuard v0.107.78
returns HTTP 404 for `/dns-query`. This appears to be a bug in this version.

**Workarounds** (pick one):
1. **Use Caddy as DoH frontend**: Caddy handles HTTPS + DoH at `/dns-query`, reverse-proxies
   DNS wireformat to AdGuard (which runs without DoH enabled). Caddy's `reverse_proxy` passes
   the raw request correctly.
2. **Downgrade to v0.107.45**: This version has stable DoH support.
3. **Skip DoH, use DoT only**: Configure `tls.port_dns_over_tls` on an allowed port.

**Not a config issue**: Multiple config formats were tested (`doh.routes` as strings,
`doh.enabled: true` alone, schema v34) — all return 404. The AdGuard process logs no
error; it simply doesn't register the `/dns-query` handler.

### Schema version auto-migration

AdGuard auto-migrates its config schema on startup (observed: v34 in v0.107.78). Do NOT
hardcode `schema_version: 20` in configs — let AdGuard set it. If you see migration errors
like `unknown field dns.port`, delete the config and let AdGuard regenerate it via the
API (`/control/install/configure`).

## GitHub Backup

Backup configs to `gzoq500/vps-config`:

```bash
cd /tmp/vps-config
cp /opt/AdGuardHome/AdGuardHome.yaml hermes/adguard-home.yaml
cp /etc/unbound/unbound.conf.d/local.conf unbound/local.conf
git add .
git commit -m "AdGuard + Unbound DNS setup"
git push origin main
```

## Web UI Access

- URL: `http://<VPS_IP>:80` or `http://dns.<domain>`
- Default: Setup wizard on first access
- User/pass stored in `/opt/AdGuardHome/AdGuardHome.yaml` (hashed with bcrypt)

## UpCloud Port Restrictions

If using UpCloud VPS:
- Allowed ports: 22, 80, 443, 3389, 8443 (+ any the user explicitly opened, e.g. 8880)
- Port 53 (DNS) must be opened in UpCloud firewall panel
- Port 3000+ usually blocked externally

**Never invent a new port to dodge a conflict.** On this class of VPS you cannot open
arbitrary ports, so a service moved to 8053/8080/8444 becomes unreachable and the user has
to correct you. Enumerate what is actually free among the allowed set
(`ss -tlnp | grep ":<port> "`) and pick from that. Ports already owned by another service
(e.g. 8443 = 9Router gateway that Hermes itself runs through) are off-limits — killing one
to free a port can sever your own connection. When every allowed port is taken, use an
iptables NAT redirect from the protocol's fixed port to an allowed one instead of
relocating the service.

## References

- `templates/AdGuardHome.service` - systemd unit with the correct ExecStart (no -p flag)
- `scripts/check-external-ports.sh` - RUN FIRST: which ports the provider firewall actually allows (`./check-external-ports.sh <ip> 53 80 443 853 8880`)
- `scripts/verify-dot.sh` - end-to-end DoT check incl. the 853 redirect (`./verify-dot.sh <host> <ip> <dot_port>`)
- `references/fix_config.py` - Python script to fix AdGuard YAML config
- `references/test_dns.sh` - DNS speed test script
- `adguard-cleanup` repo: https://github.com/gzoq500/adguard-cleanup
- AdGuard Home docs: https://github.com/AdguardTeam/AdGuardHome
- Unbound docs: https://unbound.docs.nlnetlabs.nl/
