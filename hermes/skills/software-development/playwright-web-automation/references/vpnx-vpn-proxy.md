# VPNX — Self-Hosted Rotating VPN Proxy

Docker-based VPN proxy using free VPN Gate servers. Provides SOCKS5 + HTTP proxy with REST API control.

## Repo

`https://github.com/waguriagentic/vpnx`

## What it does

Grabs free OpenVPN configs from VPN Gate public servers → creates VPN tunnel → exposes as SOCKS5 (:1080) + HTTP (:8080) proxy. REST API on :8000 for connect/rotate/disconnect.

**Multi-source fallback:** VPN Gate API → HTML scrape → GitHub mirror.

## Setup

### Option 1: Docker Hub (if available)
```bash
docker run -d --name vpnx \
  --cap-add=NET_ADMIN --device=/dev/net/tun \
  -p 1080:1080 -p 8080:8080 -p 8000:8000 \
  -e API_TOKEN=your-secret \
  mocasus/vpnx:latest
```

### Option 2: Build from source (when Docker Hub image unavailable)
```bash
git clone https://github.com/waguriagentic/vpnx.git /root/vpnx
cd /root/vpnx
docker build -t vpnx:local .
docker rm -f vpnx 2>/dev/null
docker run -d --name vpnx \
  --cap-add=NET_ADMIN --device=/dev/net/tun \
  -p 1080:1080 -p 8080:8080 -p 8000:8000 \
  -e API_TOKEN=golem-vpnx-2026 \
  --restart unless-stopped \
  vpnx:local
```

**Requires:** Docker, `/dev/net/tun` device, `NET_ADMIN` capability.

## API

All endpoints need `Authorization: Bearer <token>` header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/connect?country=JP` | Connect to VPN (auto-picks fastest if no country) |
| POST | `/rotate?country=US` | Rotate to new VPN server |
| POST | `/disconnect` | Disconnect VPN |
| GET | `/status` | VPN + proxy status |
| GET | `/locations` | List available servers by country |
| POST | `/login` | Get proxy credentials |

## Using the Proxy

```bash
# Get credentials first
curl -s http://localhost:8000/login -H "Authorization: Bearer <token>"
# Returns: {"status":"ok","proxy":{"socks5":":1080","http":":8080","username":"vpnx...","password":"..."}}

# SOCKS5
curl --socks5 user:pass@localhost:1080 https://ifconfig.me

# HTTP
curl -x http://user:pass@localhost:8080 https://ifconfig.me
```

## Available Countries (varies by time)

Typical: JP (Japan, ~42 servers), KR (Korea, ~34), VN (Vietnam), RO (Romania), US, RU.

## Integration with Captcha-Solver

Use VPNX proxy as the `proxy` parameter in captcha-solver requests:

```bash
# Solve Cloudflare through VPN
curl -X POST http://127.0.0.1:8877/solve \
  -H 'Content-Type: application/json' \
  -d '{"type":"cloudflare","url":"https://target.com","proxy":"socks5://user:pass@localhost:1080"}'
```

## Pitfalls

- **VPN Gate servers are public/blocked**: Many sites (especially Cloudflare-protected) already flag VPN Gate IPs. Not a replacement for residential proxies.
- **Connection instability**: Free VPN servers drop frequently. VPNX has a watchdog that reconnects, but expect interruptions.
- **Docker Hub image may not exist**: The `mocasus/vpnx:latest` image may not be published. Always build from source as fallback.
- **SOCKS5 auth in Python**: Use `PySocks` library (`pip install pysocks`) + monkey-patch `socket.socket = socks.socksocket`. Note: `urllib.request` with SOCKS requires PySocks, not just `requests`.
- **cf_clearance replay across proxies**: If you solve Cloudflare through VPNX's proxy, the `cf_clearance` cookie is bound to that VPN exit IP. Replaying from a different IP (or without proxy) will fail.
