---
name: adguard-home-setup
description: Install AdGuard Home on VPS with port conflict resolution.
---

# AdGuard Home Setup on VPS

## Pre-Flight Checks

1. **Check port availability** (VPS often has limited open ports):
   ```bash
   ss -tlnp | grep -E ":53 |:80 |:443 "
   ```

2. **Check for systemd-resolved conflict** (binds port 53):
   ```bash
   systemctl is-active systemd-resolved
   ss -tlnp | grep ":53 "
   ```

## Installation

```bash
curl -s https://raw.githubusercontent.com/AdguardTeam/AdGuardHome/master/scripts/install.sh | bash -s -- -v
```

## Port Conflict Resolution

If systemd-resolved blocks port 53:

```bash
systemctl mask systemd-resolved
systemctl stop systemd-resolved
```

**CRITICAL:** After stopping systemd-resolved, `/etc/resolv.conf` still points to `127.0.0.53` and DNS breaks. Fix it immediately:

```bash
# Check if resolv.conf is a symlink to systemd-resolved stub
ls -la /etc/resolv.conf

# Remove the symlink and write public DNS directly
rm -f /etc/resolv.conf
printf "nameserver 8.8.8.8\nnameserver 1.1.1.1\n" > /etc/resolv.conf

# Verify DNS works
nslookup google.com
```

If you skip this, all `curl`/`wget` to external hosts will fail with "Could not resolve host".

## Configuration

**DO NOT write AdGuardHome.yaml manually** — schema versions change between releases (e.g. v18→v19 migration breaks `clients: []` syntax). Let AdGuard generate it.

### Method 1: First-launch API setup (RECOMMENDED — no web UI needed)

Run AdGuard once, then configure via API before it enters wizard mode:

```bash
# Start AdGuard in background (first launch → wizard mode on port 3000)
cd /opt/AdGuardHome && ./AdGuardHome --no-check-update --work-dir /opt/AdGuardHome &
sleep 3

# Configure via API: set web port, DNS port, admin credentials
curl -s -X POST http://127.0.0.1:3000/control/install/configure \
  -H "Content-Type: application/json" \
  -d '{
    "web": {"ip": "0.0.0.0", "port": 80},
    "dns": {"ip": "0.0.0.0", "port": 53},
    "username": "golem",
    "password": "YOUR_PASSWORD",
    "password_repeated": "YOUR_PASSWORD"
  }'

# Kill the temp instance, then start properly via systemd
pkill -f AdGuardHome
systemctl start adguardhome
```

### Method 2: Web UI setup

If Method 1 fails, access `http://<VPS_IP>:3000` in browser and complete the setup wizard.

### Method 3: Manual YAML (advanced — schema-aware only)

Only use this if you know the exact schema version for your AdGuard release. Check with:
```bash
/opt/AdGuardHome/AdGuardHome --version  # e.g. v0.107.78 = schema 19
```

## Start AdGuard

```bash
pkill -f AdGuardHome
/opt/AdGuardHome/AdGuardHome > /var/log/adguard.log 2>&1 &
```

## Verify

```bash
# Check ports
ss -tlnp | grep -E ":53 |:80 "

# Test DNS
dig @127.0.0.1 google.com +short

# Test login
curl -s -X POST "http://127.0.0.1:80/control/login" \
  -H "Content-Type: application/json" \
  -d '{"name":"golem","password":"YOUR_PASS"}'
```

## Auto-Cleanup Cron

Use the `adguard-cleanup` script from `gzoq500/adguard-cleanup` (user's repo):

```bash
# Download to standard path
curl -sL -o /usr/local/bin/adguard-cleanup.sh \
  https://raw.githubusercontent.com/gzoq500/adguard-cleanup/main/adguard-cleanup.sh
chmod +x /usr/local/bin/adguard-cleanup.sh

# Test login first (edit USER/PASS in script if needed)
bash /usr/local/bin/adguard-cleanup.sh --test

# Install cron (daily at 3 AM)
(crontab -l 2>/dev/null; echo "0 3 * * * /usr/local/bin/adguard-cleanup.sh >> /var/log/adguard-cleanup.log 2>&1") | crontab -
```

## DoH / DoT / TLS Configuration

See `references/dot-doh-with-caddy.md` for full TLS setup with Caddy reverse proxy.

**Key pitfalls when enabling DoH/DoT:**
- `doh.routes` MUST include HTTP method prefix: `"GET /dns-query"`, `"POST /dns-query"` — NOT just `"/dns-query"`
- `doh.insecure_enabled: false` is a required boolean field
- `port_https: 0` is MANDATORY when Caddy holds 443 — without it AdGuard crashes on startup
- `port_dns_over_quic: 0` — disable unless specifically needed
- Use `certificate_path` / `private_key_path` (NOT `certificate_chain` / `private_key`)
- Bootstrap DNS must NOT point to `127.0.0.1:5335` when TLS is enabled (Unbound can't resolve hostname before TLS starts)

## Cache & Performance Optimization

See `references/dns-performance-tuning.md` for kernel, Unbound, and AdGuard cache tuning.

**Quick cache update via API (no restart needed):**
```bash
curl -s -b /tmp/agh -X POST 'http://127.0.0.1:3000/control/dns_config' \
  -H 'Content-Type: application/json' \
  -d '{"upstream_dns":["127.0.0.1:5335"],"cache_size":67108864,"cache_ttl_min":60,"cache_ttl_max":86400,"cache_enabled":true,"cache_optimistic":true}'
```

## Common Issues

- **Port 53 "closed" on port checker but actually open**: Port checker sites (yougetsignal, portchecker.io) only report "open" if there's an active listener on that port at the exact moment of the check. If AdGuard isn't running yet, port 53 will show as "closed" even though the provider allows it. **Fix**: start a temporary listener (e.g. `python3 /tmp/dns_test.py`) then re-check.
- **Port 53 in use**: Disable systemd-resolved (see Port Conflict Resolution above). Must `mask` (not just `stop`) to prevent it from restarting.
- **DNS breaks after stopping systemd-resolved**: See Port Conflict Resolution — must manually fix `/etc/resolv.conf`.
- **AdGuard fails to start with YAML errors**: Schema version mismatch (e.g. writing v18 config for v0.107.78 which expects v19). Use first-launch API method instead of manual YAML.
- **Port 80/443 in use**: Use alternative port (8080, 8880, etc.) but check VPS firewall allows it.
- **Login fails after manual config**: Password in YAML must be bcrypt-hashed. Use API method to avoid this entirely.
- **Permission denied on config after Python edit**: When writing YAML via Python, file ownership changes to root. Always `chown adguard:adguard /opt/AdGuardHome/AdGuardHome.yaml` after writing, and use tempfile+os.replace for atomic writes.
- **AdGuard crashes with `listen tcp :443: bind: address already in use`**: TLS section is trying to bind port 443 which Caddy owns. Set `port_https: 0` in the `tls` section. See references/dot-doh-with-caddy.md.
- **DoH returns 404 on /dns-query**: Check that `doh.routes` includes HTTP method prefix (`"GET /dns-query"`, not just `"/dns-query"`), and `doh.insecure_enabled: false` is set.

## Notes

- AdGuard needs TWO ports: one for web UI (HTTP) and one for DNS (53)
- On UpCloud VPS, only certain ports are externally accessible
- Never stop 9Router on port 8443 unless you need to temporarily free it
- Domain setup: point DNS A record to VPS IP, wait for propagation
- ServerMania/AraCloud: firewall is completely open (ports 1-65535) by default — if a port appears blocked, it's an internal config issue
