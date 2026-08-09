---
name: vpnx-vpn-proxy
description: VPNX — self-hosted rotating VPN proxy via Docker. Free VPN Gate servers → SOCKS5/HTTP proxy → REST API control.
triggers:
  - vpnx setup
  - rotating vpn proxy
  - socks5 proxy vpn
  - vpngate proxy
---

# VPNX — Rotating VPN Proxy

Self-hosted VPN proxy using free VPN Gate servers. No subscription needed.

## Setup (Docker)

```bash
# Clone and build
git clone https://github.com/waguriagentic/vpnx.git /root/vpnx
cd /root/vpnx && docker build -t vpnx:local .

# Run
docker run -d --name vpnx \
  --cap-add=NET_ADMIN --device=/dev/net/tun \
  -p 1080:1080 -p 8080:8080 -p 8000:8000 \
  -e API_TOKEN=golem-vpnx-2026 \
  --restart unless-stopped \
  vpnx:local
```

## API Endpoints (port 8000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/status` | VPN + proxy status |
| POST | `/connect?country=XX` | Connect to VPN (auto-picks fastest) |
| POST | `/disconnect` | Disconnect VPN |
| POST | `/rotate?country=XX` | Rotate to new server |
| GET | `/locations` | List available servers |

## Usage

```bash
# Check status
curl http://localhost:8000/status -H "Authorization: Bearer TOKEN"

# Connect to specific country
curl -X POST "http://localhost:8000/connect?country=MY" -H "Authorization: Bearer TOKEN"

# Use proxy
curl --socks5 user:pass@localhost:1080 https://ifconfig.me

# Rotate server
curl -X POST "http://localhost:8000/rotate?country=US" -H "Authorization: Bearer TOKEN"
```

## Proxy Credentials
Get from `/status` or `/login` endpoint:
```json
{"username": "vpnx32e42ccf", "password": "d1c7f431ccbdb116a18fd2b1"}
```

## Countries Available
JP (Japan), KR (Korea), VN (Vietnam), RO (Romania), US, RU (Russia) — varies by availability.

## Pitfalls
- VPN Gate servers are free/public — many are blocked by Cloudflare/anti-bot
- Connection can be unstable — use watchdog for auto-reconnect
- For residential IPs, use paid proxy services (e.g., Asocks) instead
- Docker requires `--cap-add=NET_ADMIN` and `--device=/dev/net/tun`
- SOCKS5 proxy auth credentials are auto-generated on first run
