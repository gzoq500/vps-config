# DoT/DoH with Caddy Reverse Proxy

## Problem

Caddy owns port 443 for SSL termination. AdGuard's TLS section silently tries to bind 443
on startup, causing `listen tcp :443: bind: address already in use` panic crash — even when
you only want DoT on port 853.

## Root Cause

AdGuard's `tls` section has three port fields (`port_https`, `port_dns_over_tls`,
`port_dns_over_quic`) that default to non-zero values. When `tls.enabled: true`, ALL of
them are activated.

## Required Fix

Set `port_https: 0` when Caddy holds 443. Set `port_dns_over_quic: 0` unless specifically
needed. Only `port_dns_over_tls: 853` should be non-zero.

## Working AdGuard TLS Config (YAML)

```yaml
tls:
  enabled: true
  server_name: dns.routerssh.store
  port_https: 0
  port_dns_over_tls: 853
  port_dns_over_quic: 0
  port_https: 0
  force_https: false
  certificate_path: /opt/AdGuardHome/certs/fullchain.pem
  private_key_path: /opt/AdGuardHome/certs/privkey.pem
  strict_sni_check: false
```

**CRITICAL**: Use `certificate_path` / `private_key_path` (NOT `certificate_chain` /
`private_key`). Setting the wrong pair leaves port 853 silently not listening.

## Bootstrap DNS Must Change

When TLS is enabled, bootstrap DNS must NOT point to `127.0.0.1:5335`. AdGuard needs to
resolve `dns.routerssh.store` BEFORE the TLS listener starts, but Unbound on 5335 isn't
available yet.

**Fix**: Temporarily set bootstrap to public DNS:
```yaml
bootstrap_dns:
  - 94.140.14.14
  - 94.140.15.15
```

Or keep bootstrap pointing to public DNS permanently (only used for initial hostname
resolution, not for regular queries).

## DoH Routes Format

The `doh.routes` must include HTTP method prefix:
```yaml
http:
  doh:
    insecure_enabled: false
    routes:
      - "GET /dns-query"
      - "POST /dns-query"
      - "GET /dns-query/{ClientID}"
      - "POST /dns-query/{ClientID}"
```

**NOT** just `"/dns-query"` — that returns 404.

## Cert Sync from Caddy

Caddy auto-manages Let's Encrypt certs. Sync them to AdGuard:
```bash
mkdir -p /opt/AdGuardHome/certs
cp /var/lib/caddy/.local/share/caddy/certificates/acme-v02.api.letsencrypt.org-directory/dns.routerssh.store/dns.routerssh.store.crt /opt/AdGuardHome/certs/fullchain.pem
cp /var/lib/caddy/.local/share/caddy/certificates/acme-v02.api.letsencrypt.org-directory/dns.routerssh.store/dns.routerssh.store.key /opt/AdGuardHome/certs/privkey.pem
chown -R adguard:adguard /opt/AdGuardHome/certs
chmod 600 /opt/AdGuardHome/certs/*.pem
```

**Note**: Caddy renames cert files on renewal. Add a cron job or Caddy on_exec hook to
re-sync certs after renewal, then restart AdGuard.

## Caddyfile

```
dns.routerssh.store {
    reverse_proxy 127.0.0.1:3000
}
```

Caddy handles SSL termination. AdGuard runs plain HTTP on 127.0.0.1:3000. DoH requests
go through Caddy → AdGuard. DoT requests go directly to AdGuard on port 853.

## Verification

```bash
# DoT test
kdig @dns.routerssh.store +tls -p 853 example.com +short

# DoT with explicit hostname
kdig @209.127.114.234 +tls +tls-hostname=dns.routerssh.store -p 853 google.com +short

# DoH test
curl -s 'https://dns.routerssh.store/dns-query?dns=q80BAAABAAAAAAAAB2V4YW1wbGUDY29tAAABAAE' \
  -H 'Accept: application/dns-message' | xxd | head -3

# TLS cert verification
echo | openssl s_client -connect 209.127.114.234:853 -servername dns.routerssh.store 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates
```

## Android Private DNS

Android Private DNS uses DoT on port 853 (hardcoded, cannot change). Set hostname to
`dns.routerssh.store` in Settings → Network → Private DNS.

If port 853 is blocked by the provider, native Private DNS is impossible. Workarounds:
- Use AdGuard app or Intra app (supports DoH)
- Check if provider allows opening port 853 via panel
