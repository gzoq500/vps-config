# Caddy-fronted AdGuard + Unbound + SSL Setup

Condensed working steps from session on `209.127.114.234` (dns.routerssh.store).

## Prerequisites

```bash
# Free port 53 permanently
systemctl mask systemd-resolved
systemctl stop systemd-resolved
rm -f /etc/resolv.conf
printf "nameserver 8.8.8.8\nnameserver 1.1.1.1\n" > /etc/resolv.conf
```

## Install Unbound (recursive, loopback only)

```bash
apt-get install -y unbound unbound-anchor

cat > /etc/unbound/unbound.conf << 'EOF'
server:
  interface: 127.0.0.1@5335
  interface: ::1@5335
  access-control: 127.0.0.1/8 allow
  access-control: ::1 allow
  hide-identity: yes
  hide-version: yes
  do-ipv6: no
  root-hints: /var/lib/unbound/root.hints
  do-not-query-localhost: no
  prefetch: yes
EOF

curl -sL https://www.internic.net/domain/named.root -o /var/lib/unbound/root.hints
unbound-checkconf
systemctl enable unbound && systemctl start unbound
```

Test: `dig @127.0.0.1 -p 5335 google.com +short`

## Install AdGuard Home

```bash
cd /tmp
curl -fL -o AdGuardHome_linux_amd64.tar.gz \
  "https://github.com/AdguardTeam/AdGuardHome/releases/latest/download/AdGuardHome_linux_amd64.tar.gz"
tar -xzf AdGuardHome_linux_amd64.tar.gz
mkdir -p /opt/AdGuardHome && cp AdGuardHome/AdGuardHome /opt/AdGuardHome/
chmod +x /opt/AdGuardHome/AdGuardHome
id adguard 2>/dev/null || useradd -r -s /usr/sbin/nologin adguard
chown -R adguard:adguard /opt/AdGuardHome
```

## First-launch setup via API (NOT manual YAML)

```bash
# Start AdGuard temporarily (first-launch wizard mode on :3000)
/opt/AdGuardHome/AdGuardHome --no-check-update --work-dir /opt/AdGuardHome &
sleep 3

# Configure via API - writes valid schema YAML atomically
curl -s -X POST http://127.0.0.1:3000/control/install/configure \
  -H "Content-Type: application/json" \
  -d '{
    "web": {"ip": "127.0.0.1", "port": 3000},
    "dns": {"ip": "0.0.0.0", "port": 53},
    "username": "golem",
    "password": "Kolor900@",
    "password_repeated": "Kolor900@"
  }'
# Returns "OK"

pkill -f AdGuardHome && sleep 2
```

Then set upstream to Unbound via API:
```bash
curl -s -X POST http://127.0.0.1:3000/control/login \
  -H "Content-Type: application/json" \
  -d '{"name":"golem","password":"Kolor900@"}' -c /tmp/cookie
curl -s -X POST http://127.0.0.1:3000/control/dns/upstreams \
  -H "Content-Type: application/json" -b /tmp/cookie \
  -d '{"upstreams":["127.0.0.1:5335"]}'
```

## systemd service

```bash
cat > /etc/systemd/system/adguardhome.service << 'EOF'
[Unit]
Description=AdGuard Home DNS ad blocker
After=network.target unbound.service
Wants=network.target

[Service]
Type=simple
User=adguard
Group=adguard
WorkingDirectory=/opt/AdGuardHome
ExecStart=/opt/AdGuardHome/AdGuardHome --no-check-update --work-dir /opt/AdGuardHome
Restart=always
RestartSec=5
AmbientCapabilities=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable adguardhome
systemctl start adguardhome
```

## Caddy + SSL

```bash
apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
curl -fsSL https://dl.cloudsmith.io/public/caddy/stable/gpg.key | gpg --dearmor -o /usr/share/keyrings/caddy-stable.gpg
echo "deb [signed-by=/usr/share/keyrings/caddy-stable.gpg] https://dl.cloudsmith.io/public/caddy/stable/deb/debian any-version main" \
  > /etc/apt/sources.list.d/caddy.list
apt-get update -q && apt-get install -y caddy
```

Caddyfile:
```
dns.routerssh.store {
    @doh path /dns-query
    handle @doh {
        reverse_proxy 127.0.0.1:3000
    }
    handle {
        reverse_proxy 127.0.0.1:3000
    }
}
```

```bash
systemctl start caddy   # auto-gets Let's Encrypt cert via TLS-ALPN-01
```

## Verify

```bash
# DNS direct
dig @127.0.0.1 google.com +short

# DoH via Caddy
curl -s -X POST https://dns.routerssh.store/dns-query \
  -H "Content-Type: application/dns-message" \
  --data-binary "$(echo -n 'x' | base64)" 2>&1

# Ports
ss -tulnp | grep -E ':53 |:443 |:3000 |:5335'
```

## Pitfalls encountered this session

- **Editing AdGuardHome.yaml manually** → schema migration error (v18→v19→v20).
  Fix: delete YAML, use API `/control/install/configure`.
- **`doh.routes` as YAML maps** (`- GET: /dns-query`) → silent 404 on `/dns-query`.
  Fix: use strings (`- "GET /dns-query"`).
- **systemd-resolved stopped but not masked** → comes back, re-binds 127.0.0.53:53.
  Fix: `systemctl mask` + fix `/etc/resolv.conf`.
- **`resolv.conf` still pointing to 127.0.0.53** after stopping resolved → DNS broken.
  Fix: write real nameservers directly to `/etc/resolv.conf`.
- **AdGuard port 53 binds ~10s after web UI** → premature "connection refused" looks like crash.
  Fix: wait 12-15s before asserting failure.
