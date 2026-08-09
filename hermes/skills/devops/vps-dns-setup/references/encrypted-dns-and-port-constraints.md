# Encrypted DNS (DoT/DoH) on a port-restricted VPS

Session-derived detail for AdGuard Home + Unbound on UpCloud, where the provider
firewall allows only a fixed set of ports **in both directions**.

## The hard constraint: Android Private DNS is locked to port 853

Android's "DNS Pribadi / Private DNS" field accepts a **hostname only**. The OS always
dials TCP **853** (DoT) and there is no way to specify another port. Android also has
**no native DoH support**.

Consequence: if the provider blocks inbound 853, native Private DNS can *never* connect,
no matter how correct the server is. The UI just says "Tidak dapat terhubung".

### iptables redirect does NOT rescue this

```bash
iptables -t nat -A PREROUTING -p tcp --dport 853 -j REDIRECT --to-port 8880
```

This is worth installing (it makes the setup instantly work *if* 853 is ever opened),
but it cannot fix a provider block: the packet is dropped at the provider edge and never
reaches the VM, so there is nothing for NAT to rewrite. Do not spend cycles debugging
the redirect when the root cause is upstream filtering.

## Always confirm reachability from OUTSIDE the VM

`ss -tlnp` proving a listener exists says nothing about provider filtering. Use an
external checker before concluding the config is broken:

```bash
curl -s --max-time 25 "https://portchecker.io/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"host":"<PUBLIC_IP>","ports":[853,443,8880,53]}'
# -> {"check":[{"port":853,"status":false},{"port":443,"status":true},...]}
```

Observed on this UpCloud host: 80, 443, 3389, 8443, 8880 open; **853 and 53/tcp closed**.

## Outbound egress is filtered too

Egress is restricted to the same style of allowlist. Verified with a neutral host so the
result is not confused with a remote-side outage:

```bash
timeout 8 bash -c 'echo > /dev/tcp/portquiz.net/8080'   # OPEN
timeout 8 bash -c 'echo > /dev/tcp/portquiz.net/6080'   # blocked
timeout 8 bash -c 'echo > /dev/tcp/google.com/5228'     # blocked
```

Practical impact: the Hermes browser tool runs *on this VPS*, so any web console on a
non-allowed port (e.g. a noVNC panel on `:6080`) fails with `This site can't be reached`
/ CDP `Page.navigate` timeout. That is the provider firewall, not a broken browser.
Diagnose by testing the same host on 80/443 — if those connect and ping works, the host
is fine and only the high port is filtered. Ask for a `:443` console URL or SSH instead.

## Port layout that actually works when 853 is blocked

Put the encrypted endpoints on ports that are already open, and keep Unbound private.

| Service | Port | Notes |
|---|---|---|
| AdGuard web UI | 80 | plain HTTP |
| AdGuard **DoH** | 443 | `tls.port_https: 443` → clean URL, no port in URL |
| AdGuard **DoT** | 8880 | `tls.port_dns_over_tls: 8880` |
| AdGuard plain DNS | 53 | UDP/TCP, for manual-IP clients on LAN/Wi-Fi |
| Unbound recursive | 127.0.0.1:5335 | localhost only — AdGuard's sole upstream |

Unbound must be moved off 443 to free it for DoH:

```bash
sed -i 's/^  port: 443/  port: 5335/; s/^  interface: 0.0.0.0/  interface: 127.0.0.1/' \
  /etc/unbound/unbound.conf.d/local.conf
unbound-checkconf && systemctl restart unbound
```

Then AdGuard `dns.upstream_dns: ['127.0.0.1:5335']`. Binding Unbound to localhost is
strictly better: it cannot be abused as an open resolver and still leaks nothing because
it resolves recursively from `root.hints`.

## Real Let's Encrypt cert (self-signed is rejected by Android/most clients)

certbot standalone needs port 80, so stop whatever holds it first:

```bash
apt-get install -y certbot
pkill -f AdGuardHome; sleep 2            # free :80
certbot certonly --standalone --non-interactive --agree-tos \
  --register-unsafely-without-email -d dns.routerssh.web.id --http-01-port 80
```

Cert lands at `/etc/letsencrypt/live/<domain>/{fullchain.pem,privkey.pem}`.

Auto-restart AdGuard on renewal (otherwise it serves the expired cert until reboot):

```bash
mkdir -p /etc/letsencrypt/renewal-hooks/deploy
printf '#!/bin/bash\nsystemctl restart AdGuardHome\n' \
  > /etc/letsencrypt/renewal-hooks/deploy/restart-adguard.sh
chmod +x /etc/letsencrypt/renewal-hooks/deploy/restart-adguard.sh
```

## Correct AdGuard TLS YAML keys

The keys are `certificate_path` / `private_key_path`. Using `certificate_chain` /
`private_key` silently leaves TLS unarmed — no listener appears on the DoT/DoH port and
the log shows nothing about TLS.

```python
import yaml
p = '/opt/AdGuardHome/AdGuardHome.yaml'
c = yaml.safe_load(open(p))
c['tls'] = {
    'enabled': True,
    'server_name': 'dns.routerssh.web.id',
    'certificate_path': '/etc/letsencrypt/live/dns.routerssh.web.id/fullchain.pem',
    'private_key_path': '/etc/letsencrypt/live/dns.routerssh.web.id/privkey.pem',
    'port_https': 443,            # DoH
    'port_dns_over_tls': 8880,    # DoT
    'allow_unencrypted_doh': False,
}
yaml.dump(c, open(p, 'w'), default_flow_style=False)
```

Success in `/var/log/adguard.log`:

```
tls_manager: parsing multiple pem certificates num=1
dnsproxy: creating tls server socket addr=0.0.0.0:8880
```

## Verifying DoT and DoH for real

Install `kdig` — plain `dig` cannot speak DoT:

```bash
apt-get install -y knot-dnsutils

kdig @dns.routerssh.web.id +tls +tls-hostname=dns.routerssh.web.id -p 8880 example.com
# want: ";; TLS ... The certificate is trusted." and an ANSWER SECTION
```

TLS chain alone:

```bash
echo | openssl s_client -connect dns.routerssh.web.id:8880 \
  -servername dns.routerssh.web.id 2>&1 | grep -E "subject=|issuer=|Verify return"
# want: Verify return code: 0 (ok)
```

DoH — must use **wireformat**, not the JSON API. AdGuard returns `400 Bad Request` for
`accept: application/dns-json`; that is not a failure of the endpoint:

```bash
curl -s -o /tmp/doh.bin -w "HTTP %{http_code}\n" \
  "https://dns.routerssh.web.id/dns-query?dns=q80BAAABAAAAAAAAB2V4YW1wbGUDY29tAAABAAE" \
  -H "accept: application/dns-message"
xxd /tmp/doh.bin | head -3   # want HTTP 200 + binary DNS response
```

## Client options when 853 stays blocked

- **Intra** (Jigsaw) or the **AdGuard** Android app: accept a DoH URL and apply it
  system-wide via a local VPN service. This is the practical replacement for native
  Private DNS.
- **Chrome**: Settings → Privacy and security → Use secure DNS → Custom → DoH URL.
- **Plain DNS fallback**: Wi-Fi → static IP → DNS = server IP. Works, but unencrypted
  and only on that one network.

Leave the native "Private DNS" toggle **Nonaktif** — it will keep reporting
"Tidak dapat terhubung" forever while 853 is filtered.

## AdGuard systemd unit

The bundled installer writes `ExecStart=... -s run`, which fails when you re-register the
unit by hand. Write a plain unit instead:

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

If `systemctl` reports `activating (auto-restart)` in a loop, the stale unit file is
still on disk — `rm /etc/systemd/system/AdGuardHome.service`, re-copy, `daemon-reload`.

**Startup timing:** AdGuard binds the web port immediately but the DNS listener comes up
roughly **10 seconds later** (`dnsproxy: starting dns proxy server`). Sleep 14-16s before
asserting that port 53 / DoT failed to bind, otherwise you will chase a phantom bug.

## Persist iptables rules

```bash
DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent
mkdir -p /etc/iptables
iptables-save > /etc/iptables/rules.v4
```

If `apt` hangs on the interactive save prompt and leaves dpkg wedged:

```bash
DEBIAN_FRONTEND=noninteractive dpkg --configure -a
```
