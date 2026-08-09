---
name: vps-dns-setup
description: Install AdGuard Home and Unbound DNS on port-restricted VPS.
trigger: User asks to install DNS server, AdGuard, Unbound, or setup DNS on VPS with port restrictions.
---

# VPS DNS Setup (AdGuard Home + Unbound)

## Use Case
- VPS with restricted ports (UpCloud: only 22, 80, 443, 8443, 3389 allowed)
- Need ad-blocking DNS (AdGuard) + local resolver (Unbound)
- Port 53 conflicts with systemd-resolved

## Prerequisites
- VPS with root access
- Ports 80, 443, 53 available (or can free them)
- `systemd-resolved` disabled (uses port 53)

## Step-by-Step

### 1. Free Port 53 (Disable systemd-resolved)
```bash
systemctl stop systemd-resolved
systemctl disable systemd-resolved
systemctl mask systemd-resolved
```

### 2. Install AdGuard Home
```bash
curl -s https://raw.githubusercontent.com/AdguardTeam/AdGuardHome/master/scripts/install.sh | bash -s -- -v
```

### 3. Install AdGuard Home (Manual Download - RELIABLE)
Install script sering gagal silent. Download manual:
```bash
cd /tmp
wget -q https://github.com/AdguardTeam/AdGuardHome/releases/latest/download/AdGuardHome_linux_amd64.tar.gz
tar -xzf AdGuardHome_linux_amd64.tar.gz
mkdir -p /opt/AdGuardHome
cp AdGuardHome/AdGuardHome /opt/AdGuardHome/
chmod +x /opt/AdGuardHome/AdGuardHome
useradd -r -s /usr/sbin/nologin adguard 2>/dev/null
chown -R adguard:adguard /opt/AdGuardHome
```

### 4. Configure AdGuard (Schema v34+ - JANGAN EDIT MANUAL)
AdGuard v0.107.78+ uses schema_version 34. Manual YAML editing sering rusak karena:
- `interval` must be duration string (e.g. `24h`), not integer
- `doh.routes` format changed
- `bootstrap_dns` format strict

**PREFERRED METHOD: Let AdGuard generate config otomatis, then modify via API.**
```bash
# First run - generates config
cd /opt/AdGuardHome && ./AdGuardHome --no-check-update --work-dir /opt/AdGuardHome &
sleep 5
# Complete setup via API (see below)
```

**If must edit YAML:** Use Python, not manual text editor:
```python
import yaml
with open('/opt/AdGuardHome/AdGuardHome.yaml', 'r') as f:
    config = yaml.safe_load(f)
# Modify config dict
config['dns']['upstream_dns'] = ['127.0.0.1:5335']
with open('/opt/AdGuardHome/AdGuardHome.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False)
```

**Known-good config template:** See `templates/adguard-home-v34.yaml`

ATUR CARA PAKAI PYTHON: `python3 script_above.py` → hindari YAML syntax error manual.

**Password hashing:**
```bash
pip install bcrypt
python3 -c "import bcrypt; print(bcrypt.hashpw(b'${ADGUARD_PASS}', bcrypt.gensalt()).decode())"
```

**Jika AdGuard crash dengan error "timeout opening sessions.db":**
```bash
rm -f /opt/AdGuardHome/data/sessions.db
chown -R root:root /opt/AdGuardHome/data/
```

### 5. Setup AdGuard via API (After First Run)
```bash
# Login
curl -s -c /tmp/agh_cookie -X POST http://127.0.0.1:3000/control/login \
  -H "Content-Type: application/json" \
  -d '{"name":"golem","password":"Kolor900@"}' -o /dev/null

# Set upstream to Unbound
curl -s -b /tmp/agh_cookie -X POST http://127.0.0.1:3000/control/dns/config \
  -H "Content-Type: application/json" \
  -d '{"upstream_dns":["127.0.0.1:5335"],"bootstrap_dns":["127.0.0.1:5335"]}'
```

### 6. Install Unbound (Recursive Resolver - No Leaks)
```bash
apt-get install -y unbound
curl -s https://www.internic.net/domain/named.root -o /var/lib/unbound/root.hints
```

Config `/etc/unbound/unbound.conf.d/local.conf` (RECURSIVE, bukan forward):
```yaml
server:
  port: 443  # Use allowed port (443/8880)
  interface: 0.0.0.0
  access-control: 0.0.0.0/0 allow
  do-ip4: yes
  do-ip6: no
  root-hints: /var/lib/unbound/root.hints  # CRITICAL: recursive resolver
  # Cache optimasi
  msg-cache-size: 64m
  rrset-cache-size: 128m
  prefetch: yes
  serve-expired: yes
```

**JANGAN PAKAI `forward-zone`** → itu akan bocor keluar. `root-hints` membuat Unbound query langsung ke root DNS servers (no leaks).

### 7. Caddy + SSL for DoH (dns.routerssh.store)
```bash
apt-get install -y caddy
cat > /etc/caddy/Caddyfile << 'EOF'
dns.routerssh.store {
    # DNS-over-HTTPS (DoH)
    @doh path /dns-query
    handle @doh {
        reverse_proxy 127.0.0.1:3000
    }
    # AdGuard web panel
    handle {
        reverse_proxy 127.0.0.1:3000
    }
}
EOF
systemctl enable caddy && systemctl start caddy
# Caddy auto-gets Let's Encrypt cert for dns.routerssh.store
```

### 8. AdGuard DoH/DoT (Optional - Advanced)
AdGuard DoH config is tricky in v0.107.78. Two options:
1. **Let Caddy handle DoH** (recommended): Caddy reverse proxies `/dns-query` to AdGuard
2. **Enable AdGuard DoH**: Add `doh.enabled: true` in YAML, but format is strict

DoT (port 853): AdGuard needs TLS cert. Copy from Caddy:
```bash
mkdir -p /opt/AdGuardHome/certs
cp /var/lib/caddy/.local/share/caddy/certificates/acme-v02.api.letsencrypt.org-directory/dns.routerssh.store/* /opt/AdGuardHome/certs/
chown -R adguard:adguard /opt/AdGuardHome/certs
```
Then add `tls` section in AdGuard YAML (see pitfalls).

### 9. Fix DNS Resolution (CRITICAL)
After stopping systemd-resolved, `/etc/resolv.conf` still points to `127.0.0.53` → DNS broken.
```bash
rm -f /etc/resolv.conf
printf "nameserver 8.8.8.8\nnameserver 1.1.1.1\n" > /etc/resolv.conf
```

## Pitfalls
- **Port 53 blocked:** `systemctl mask systemd-resolved` (not just stop). Also fix `/etc/resolv.conf` manually after masking (see step 9).
- **AdGuard YAML schema errors:** v0.107.78 uses schema_version 34. Manual edits often break `interval` (must be duration string like `2160h`, not integer), `doh.routes` format, or `bootstrap_dns` format. Let AdGuard generate config first, then modify via API or careful Python YAML editing.
- **AdGuard DoH "Not Found":** DoH in v0.107.78 requires exact config format. If `doh.enabled: true` still gives 404, use Caddy to handle DoH instead (reverse proxy `/dns-query` to AdGuard).
- **AdGuard DoT crash:** If AdGuard tries to bind port 443 (already used by Caddy), it crashes. DoT must use port 853 with `tls` section, not web HTTPS.
- **AdGuard `permission denied` writing config:** User `adguard` must own `/opt/AdGuardHome/` recursively. Fix: `chown -R adguard:adguard /opt/AdGuardHome`.
- **DNS broken after stopping systemd-resolved:** `/etc/resolv.conf` still has `nameserver 127.0.0.53`. Must manually replace with public DNS (see step 9).
- **AdGuard password:** Must be bcrypt hash, not plaintext. Generate: `python3 -c "import bcrypt; print(bcrypt.hashpw(b'PASS', bcrypt.gensalt()).decode())"`.
- **AdGuard session.db corrupt:** If AdGuard crashes with "timeout opening sessions.db", delete: `rm -f /opt/AdGuardHome/data/sessions.db`.
- **Unbound recursive vs forward:** For no DNS leaks, Unbound must use `root-hints` (recursive), not `forward-zone`. Config: `root-hints: /var/lib/unbound/root.hints`.
- **Unbound port:** Install on `127.0.0.1:5335` (not public port) to avoid open-resolver abuse and free 443 for DoH.
- **Android Private DNS is hard-locked to port 853** and has NO native DoH. If provider blocks inbound 853, native Private DNS can never connect. Use DoH on 443 + Intra/AdGuard app.
- **Always verify reachability from OUTSIDE.** `ss -tlnp` showing listener proves nothing about provider filtering. Use `curl -s "https://ports.yougetsignal.com/check-port.php" -d "remoteAddress=IP&portNumber=53"` before blaming config.
- **Egress is filtered too.** Outbound to non-allowlisted high ports fails. Test with `curl https://portquiz.net:443` (works) vs `:8080` (fails).
- **AdGuard TLS keys:** Use `certificate_path` / `private_key_path` (not `certificate_chain` / `private_key`).
- **Self-signed certs rejected by Android.** Get real cert via Caddy/LetsEncrypt.
- **AdGuard DNS listener binds ~10s AFTER web port.** Sleep 14-16s before concluding port 53 failed.
- **`dig` cannot test DoT.** Use `kdig @host +tls +tls-hostname=domain -p port`. For DoH use proper wire format (not JSON API).
- **UpCloud/ServerMania firewall:** Only ports 22, 80, 443, 8443, 3389, 8880, 51820 typically open. Ports 53/853 may be blocked upstream (test from outside!).
- **Install script unreliable:** `curl | bash` install script often fails silent. Download binary manually (see step 3).

## Verification
```bash
# DNS resolution
dig @127.0.0.1 -p 443 google.com +short

# AdGuard API
curl -X POST http://127.0.0.1:80/control/login -H "Content-Type: application/json" -d '{"name":"golem","password":"PASS"}'

# Port check
ss -tlnp | grep -E "80|443|53"
```

## References
- **`references/encrypted-dns-and-port-constraints.md`** — DoT/DoH on a port-restricted VPS: the Android-853 lock, external port verification, egress filtering (breaks web consoles on high ports), working port layout (DoH 443 / DoT 8880 / Unbound 127.0.0.1:5335), Let's Encrypt + renewal hook, correct AdGuard TLS keys, kdig/openssl/DoH-wireformat verification, systemd unit and startup timing.
- `templates/adguard-home.yaml` — known-good AdGuard config to copy and modify.
- AdGuard Home: https://github.com/AdguardTeam/AdGuardHome
- Unbound docs: https://unbound.docs.nlnetlabs.nl/
- UpCloud firewall: Only allow ports 22, 80, 443, 8443, 3389, 8880 (853 and 53/tcp cannot be opened)
