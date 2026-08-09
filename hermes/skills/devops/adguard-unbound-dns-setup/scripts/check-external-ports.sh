#!/bin/bash
# Check which ports are actually reachable from OUTSIDE the VPS.
#
# `ss -tlnp` and `iptables -L` only show local state — they say nothing about a
# provider-level firewall (UpCloud, Vultr, Tencent security groups). Run this BEFORE
# assuming a service is unreachable because of its own config, and before adding an
# iptables NAT redirect (a redirect cannot rescue a port the provider drops upstream).
#
# Usage: ./check-external-ports.sh <VPS_IP> [port ...]
#        ./check-external-ports.sh 95.111.195.148 53 80 443 853 8880

set -u

IP="${1:-}"
if [ -z "$IP" ]; then
    echo "Usage: $0 <VPS_IP> [port ...]" >&2
    exit 1
fi
shift

PORTS=("$@")
if [ ${#PORTS[@]} -eq 0 ]; then
    PORTS=(22 53 80 443 853 3389 8443 8880)
fi

echo "External reachability for $IP"
echo "-----------------------------------"

for P in "${PORTS[@]}"; do
    RESP=$(curl -s --max-time 20 "https://portchecker.io/api/v1/query" \
        -H "Content-Type: application/json" \
        -d "{\"host\":\"$IP\",\"ports\":[$P]}" 2>/dev/null)

    case "$RESP" in
        *'"status":true'*)  echo "  $P  OPEN" ;;
        *'"status":false'*) echo "  $P  BLOCKED (provider firewall or nothing listening)" ;;
        *)                  echo "  $P  UNKNOWN (check failed: ${RESP:-no response})" ;;
    esac
done

cat <<'NOTE'

Interpretation:
  OPEN     - reachable; safe to serve a protocol here or target it with a NAT redirect.
  BLOCKED  - either no listener OR the provider drops it upstream. Cross-check with
             `ss -tlnp | grep ":<port> "`. If something IS listening locally but this
             says BLOCKED, the provider firewall is the cause and only the provider
             panel can fix it. Do NOT try to work around it with iptables.

Android Private DNS note: DoT is hardcoded to port 853 and cannot be changed in the OS
settings. If 853 is BLOCKED, native Private DNS cannot work at all — offer DoT on an
allowed port (for clients that accept a port) or DoH via an app instead.
NOTE
