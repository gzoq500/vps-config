# DNS Server Performance Tuning

## Kernel Network Optimizations

Apply to `/etc/sysctl.conf`:

```bash
# Network buffers (16MB for high-throughput DNS)
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.core.rmem_default = 1048576
net.core.wmem_default = 1048576

# TCP optimizations
net.ipv4.tcp_fastopen = 3          # Client+server fast open
net.ipv4.tcp_congestion_control = bbr  # BBR > cubic for DNS
net.ipv4.tcp_mtu_probing = 1       # Avoid fragmentation
net.ipv4.tcp_tw_reuse = 1          # Reuse TIME_WAIT sockets
net.ipv4.tcp_fin_timeout = 15      # Faster FIN close
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_intvl = 15
net.ipv4.tcp_keepalive_probes = 5

# Network backlog
net.core.netdev_max_backlog = 16384
net.core.somaxconn = 8192

# UDP buffers (critical for DNS)
net.ipv4.udp_rmem_min = 8192
net.ipv4.udp_wmem_min = 8192
```

Load and apply:
```bash
modprobe tcp_bbr 2>/dev/null || echo "BBR not available"
sysctl -p
sysctl net.ipv4.tcp_congestion_control  # Verify BBR
```

## Unbound Cache Tuning

Config at `/etc/unbound/unbound.conf`:

```
server:
    # Cache sizes (64MB msg, 128MB rrset)
    msg-cache-size: 64m
    rrset-cache-size: 128m
    msg-cache-slabs: 4
    rrset-cache-slabs: 4

    # TTL settings
    cache-max-ttl: 86400
    cache-min-ttl: 60

    # Prefetch & serve-expired
    prefetch: yes
    prefetch-key: yes
    serve-expired: yes
    serve-expired-ttl: 86400
    serve-expired-reply-ttl: 5

    # Performance
    num-threads: 2              # Match CPU cores
    so-reuseport: yes           # Per-thread sockets
    so-rcvbuf: 4m
    so-sndbuf: 4m
    minimal-responses: yes      # Smaller DNS packets
    rrset-roundrobin: yes       # Distribute load

    # EDNS
    edns-buffer-size: 1232
    max-udp-size: 1232
```

Restart: `systemctl restart unbound`

## AdGuard Cache Tuning

**Via API (no restart needed):**
```bash
curl -s -b /tmp/agh -X POST 'http://127.0.0.1:3000/control/dns_config' \
  -H 'Content-Type: application/json' \
  -d '{
    "upstream_dns": ["127.0.0.1:5335"],
    "bootstrap_dns": ["127.0.0.1:5335"],
    "protection_enabled": true,
    "rate_limit": 0,
    "cache_size": 67108864,
    "cache_ttl_min": 60,
    "cache_ttl_max": 86400,
    "cache_enabled": true,
    "cache_optimistic": true,
    "upstream_timeout": 5,
    "blocking_mode": "default"
  }'
```

- `cache_size: 67108864` = 64MB (default is 4MB)
- `cache_optimistic: true` = serve stale cache while refreshing in background
- `rate_limit: 0` = no rate limiting (for personal DNS server)

**Via YAML (requires restart):**
```yaml
dns:
  cache_size: 67108864
  cache_ttl_min: 60
  cache_ttl_max: 86400
  cache_enabled: true
  cache_optimistic: true
  upstream_timeout: 5
```

## Expected Performance (Buffalo NY VPS)

| Metric | Before | After |
|--------|--------|-------|
| DNS cache hit | 18ms | 17-19ms |
| DNS cache miss | 20-78ms | 40-70ms |
| Ping 8.8.8.8 | 12.5ms | 12.2ms |
| DoH burst avg | 54ms | 40-50ms |
| DoT burst avg | 78ms | 65-75ms |

**Note**: Ping is limited by physical distance (Buffalo NY → nearest Google PoP). Cannot
go below ~12ms without moving VPS closer to users.

## Verification

```bash
# Unbound cache stats
unbound-control stats | grep -E 'total.num.queries|cachehits|cachemiss|recursive.time'

# AdGuard cache config
curl -s -b /tmp/agh 'http://127.0.0.1:3000/control/dns_info' | python3 -c "
import sys, json; d = json.load(sys.stdin)
print('cache_size:', d.get('cache_size'))
print('cache_enabled:', d.get('cache_enabled'))
print('cache_optimistic:', d.get('cache_optimistic'))
"

# Benchmark DNS latency
for i in 1 2 3; do
  start=$(date +%s%N)
  dig @127.0.0.1 google.com +short +time=3 > /dev/null
  end=$(date +%s%N)
  echo "$(( (end - start) / 1000000 ))ms"
done
```
