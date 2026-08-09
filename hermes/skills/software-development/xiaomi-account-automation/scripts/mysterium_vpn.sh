#!/bin/bash
# Mysterium VPN helper script
# Usage: ./mysterium_vpn.sh [connect|disconnect|status|ip|providers]

MYST_API="http://127.0.0.1:4050"
IDENTITY="${MYST_IDENTITY:-0x207d5e9f24b13e4569444f1f6dc4005480f61f68}"

case "$1" in
    status)
        curl -s "$MYST_API/healthcheck" 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Daemon: UP ({d[\"version\"]})')" 2>/dev/null || echo "Daemon: DOWN"
        curl -s "$MYST_API/connection" 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'VPN: {d[\"status\"]}')" 2>/dev/null || echo "VPN: Not connected"
        ;;
    connect)
        PROVIDER="${2:-0xfb2c166c4373a01535ce983596bb9a489c9b67eb}"
        echo "Unlocking..."
        curl -s -X PUT "$MYST_API/identities/$IDENTITY/unlock" -H "Content-Type: application/json" -d '{"passphrase":"${VPS_PASS}500"}'
        echo ""
        echo "Connecting to ${PROVIDER:0:20}..."
        curl -s -X PUT "$MYST_API/connection" -H "Content-Type: application/json" \
            -d "{\"consumer_id\":\"$IDENTITY\",\"provider_id\":\"$PROVIDER\",\"connect_options\":{\"dns\":\"8.8.8.8\"}}"
        echo ""
        sleep 10
        curl -s "$MYST_API/connection" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Status: {d[\"status\"]}')" 2>/dev/null
        ;;
    disconnect)
        curl -s -X DELETE "$MYST_API/connection"
        echo "Disconnected"
        ;;
    ip)
        echo "=== Current IP ==="
        curl -s --max-time 10 https://ipinfo.io/json 2>/dev/null | python3 -c "
import json,sys
d = json.load(sys.stdin)
print(f'IP: {d[\"ip\"]}')
print(f'Location: {d[\"city\"]}, {d[\"country\"]}')
print(f'Org: {d[\"org\"]}')
" 2>/dev/null || echo "Failed to get IP"
        ;;
    providers)
        COUNTRY="${2:-ID}"
        curl -s "$MYST_API/proposals?ip_type=residential" 2>/dev/null | python3 -c "
import json,sys
d = json.load(sys.stdin)
props = [p for p in d.get('proposals',[]) if p['location'].get('country')=='$COUNTRY' and not p.get('access_policies')]
print(f'$COUNTRY residential: {len(props)} providers')
for p in sorted(props, key=lambda x: x['quality']['quality'], reverse=True)[:10]:
    print(f'  {p[\"location\"][\"city\"]} | {p[\"location\"][\"isp\"][:30]} | Q:{p[\"quality\"][\"quality\"]:.1f}')
    print(f'    ID: {p[\"provider_id\"]}')
" 2>/dev/null
        ;;
    *)
        echo "Usage: $0 {status|connect [provider_id]|disconnect|ip|providers [country]}"
        echo ""
        echo "Examples:"
        echo "  $0 status                    # Check daemon and VPN status"
        echo "  $0 connect                   # Connect to default US residential"
        echo "  $0 connect PROVIDER_ID       # Connect to specific provider"
        echo "  $0 disconnect                # Disconnect VPN"
        echo "  $0 ip                        # Check current IP and location"
        echo "  $0 providers ID              # List Indonesia residential providers"
        ;;
esac
