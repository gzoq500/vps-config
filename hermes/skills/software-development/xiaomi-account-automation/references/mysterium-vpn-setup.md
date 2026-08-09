# Mysterium VPN — Residential Proxy for Risk Control Bypass

## Overview
Mysterium Network provides decentralized residential VPN. Used to bypass MiMo's risk control (error 400909) which detects datacenter IPs.

## Installation
```bash
curl -L -o /tmp/mysterium.deb "https://github.com/mysteriumnetwork/mysterium-vpn-desktop/releases/download/10.17.10/mysterium-vpn-desktop_10.17.10_amd64.deb"
dpkg-deb -x /tmp/mysterium.deb /tmp/mysterium_extracted
cp /tmp/mysterium_extracted/opt/MysteriumDark/resources/app.asar.unpacked/node_modules/@mysteriumnetwork/node/bin/linux/x64/myst /usr/local/bin/myst
chmod +x /usr/local/bin/myst
# Verify: myst version → 1.29.2
```

## Keystore
- Location: `/root/.mysterium/keystore/`
- Naming: `UTC--<timestamp>--<address_without_0x>`
- Permissions: `chmod 600` (REQUIRED — daemon ignores files with wrong permissions)
- MAC uses **Keccak-256** (NOT SHA-256). Use `Crypto.Hash.keccak`.
- **Use ORIGINAL keystore with ORIGINAL password** — re-encrypted keystores fail unlock
- Empty response on unlock = success. 403 = wrong password.

## Daemon Setup

### Start daemon
```bash
myst daemon  # port 4050, creates /root/.mysterium/mainnet/db/
curl http://127.0.0.1:4050/healthcheck
```

### DNS Script Fix (REQUIRED)
Without this, connections fail with "could not set DNS"
```bash
mkdir -p /usr/local/bin/config
cat > /usr/local/bin/config/update-resolv-conf << 'EOF'
#!/bin/bash
case "$1" in
    up) cp /etc/resolv.conf /etc/resolv.conf.myst-backup 2>/dev/null
        echo "nameserver ${MYS_DNS_SERVERS:-8.8.8.8}" > /etc/resolv.conf ;;
    down) [ -f /etc/resolv.conf.myst-backup ] && cp /etc/resolv.conf.myst-backup /etc/resolv.conf ;;
esac
EOF
chmod +x /usr/local/bin/config/update-resolv-conf
cat > /usr/local/bin/config/nonpriv-ip << 'EOF'
#!/bin/bash
echo "0.0.0.0"
EOF
chmod +x /usr/local/bin/config/nonpriv-ip
```

### Unlock identity (PUT, not POST!)
```bash
curl -X PUT http://127.0.0.1:4050/identities/0xADDR/unlock \
  -H 'Content-Type: application/json' -d '{"passphrase":"PW"}'
# Empty response = success. 403 = wrong password.
```

### Find providers (no access_policies)
```bash
curl 'http://127.0.0.1:4050/proposals?ip_type=residential&quality_min=2.0' | python3 -c "
import json,sys
d = json.load(sys.stdin)
props = [p for p in d['proposals'] if not p.get('access_policies')]
for p in sorted(props, key=lambda x: x['quality']['quality'], reverse=True)[:10]:
    print(f'{p[\"location\"][\"city\"]} | {p[\"location\"][\"country\"]} | Q:{p[\"quality\"][\"quality\"]:.1f} | {p[\"provider_id\"][:30]}')
"
```

### Connect
```bash
curl -X PUT http://127.0.0.1:4050/connection \
  -H 'Content-Type: application/json' \
  -d '{"consumer_id":"0xADDR","provider_id":"0xPROV","connect_options":{"dns":"8.8.8.8"}}'
# Wait 15-20s, then check:
curl http://127.0.0.1:4050/connection
```

## Network Routing
Mysterium creates a `tun0` interface. **ALL traffic routes through it automatically** — no need to configure proxy in Playwright or requests. Just connect VPN before running scripts. Verify: `curl https://ipinfo.io/json` should show residential IP.

## Confirmed Working (2026-07-19)
- **Default provider**: `0xfb2c166c4373a01535ce983596bb9a489c9b67eb` (US/Dallas residential)
- **IP**: `170.75.255.230` — AS393398, 1515 ROUNDTABLE DR PROPERTY, LLC
- **Proxy detection**: NOT detected as proxy or tor
- **Indonesia providers**: 611 total (Jambi Q:3.0, Jakarta Q:2.3, Yogyakarta Q:2.8)

## Helper Script
`/root/mysterium_vpn.sh` — status/connect/disconnect/ip/providers

## Troubleshooting
| Error | Fix |
|-------|-----|
| unlock required | PUT /identities/.../unlock with passphrase |
| Unlock failed 403 | Use ORIGINAL keystore with ORIGINAL password |
| could not set DNS | Create /usr/local/bin/config/update-resolv-conf |
| identity not allowed | Provider has access_policies, filter them out |
| port 4050 in use | kill old myst daemon first |
| Already exited immediately | Check if port is in use; kill stale daemon |
| healthcheck fails (curl returns empty) | Daemon died silently — restart: `myst daemon` (background) |
| All providers reject identity | Daemon may need restart; try unlock → connect sequence again |

## Daemon Restart Pattern
The daemon can die silently (process exits). Always check health before connecting:
```bash
curl -s http://127.0.0.1:4050/healthcheck || (myst daemon &) && sleep 12
```

## Provider Rotation (3-5 attempts)
When "consumer identity is not allowed" occurs, iterate through multiple providers:
```bash
for pid in "PROV1" "PROV2" "PROV3" "PROV4" "PROV5"; do
    R=$(curl -s --max-time 15 -X PUT "http://127.0.0.1:4050/connection" \
      -H "Content-Type: application/json" \
      -d "{\"consumer_id\":\"0xADDR\",\"provider_id\":\"$pid\",\"connect_options\":{\"dns\":\"8.8.8.8\"}}")
    if echo "$R" | grep -q "Connected\|already exists"; then
        echo "CONNECTED to $pid"; break
    fi
    sleep 2
done
```

## Clean-Before-Run Pattern (user preference)
User explicitly wants: disconnect → clean → reconnect → verify IP → then run automation.
```bash
# 1. Disconnect
curl -s -X DELETE "http://127.0.0.1:4050/connection"
sleep 5
# 2. Unlock (required each reconnect)
curl -s -X PUT "http://127.0.0.1:4050/identities/0xADDR/unlock" \
  -H "Content-Type: application/json" -d '{"passphrase":"PW"}'
sleep 2
# 3. Connect to provider
curl -s -X PUT "http://127.0.0.1:4050/connection" -H "Content-Type: application/json" \
  -d '{"consumer_id":"0xADDR","provider_id":"0xPROV","connect_options":{"dns":"8.8.8.8"}}'
sleep 15
# 4. Verify new IP
curl -s https://ipinfo.io/json | grep '"ip"'
```

## IP Verification
Always verify IP changed AFTER VPN reconnect:
```bash
curl -s --max-time 10 https://ipinfo.io/json
# Check: city, country, org (should be residential ISP, NOT datacenter)
```
