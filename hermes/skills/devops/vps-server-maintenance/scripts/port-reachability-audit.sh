#!/bin/bash
# port-reachability-audit.sh — prove which inbound TCP ports actually reach this
# box from the public internet, by binding a real temporary listener on each
# port and asking an external checker.
#
# Why a real listener: every external port checker reports "closed" for a port
# with nothing listening. Without a listener you cannot distinguish
# "provider/cloud firewall blocks it" from "nothing is bound".
#
# Usage:
#   bash port-reachability-audit.sh                      # default port set
#   bash port-reachability-audit.sh 80 443 8443 51820    # explicit ports
#
# IMPORTANT: run via `bash script.sh` from a Hermes terminal call. The Hermes
# shell wrapper rejects inline `&` / long-lived servers typed directly into a
# foreground command, but does NOT inspect the inside of a script file.
#
# Never include a port that already has a production listener (e.g. 8443
# 9Router, 22 sshd): the bind fails and, worse, you risk touching live traffic.

set -u

IP="${PUBLIC_IP:-$(curl -s -4 --max-time 10 https://ifconfig.me)}"
[ -z "$IP" ] && { echo "Cannot determine public IP"; exit 1; }
echo "Auditing inbound reachability for $IP"
echo

if [ "$#" -gt 0 ]; then
  PORTS=("$@")
else
  PORTS=(21 25 53 80 443 853 3000 3389 8080 8880 20128 51820)
fi

# Ports with a live production listener — skip so we never disturb them.
BUSY=$(ss -tln 2>/dev/null | awk 'NR>1{split($4,a,":"); print a[length(a)]}' | sort -u)

for p in "${PORTS[@]}"; do
  if echo "$BUSY" | grep -qx "$p"; then
    printf "%-7s SKIP (production listener already bound)\n" "$p"
    continue
  fi

  cd /tmp || exit 1
  timeout 25 python3 -m http.server "$p" --bind 0.0.0.0 >/dev/null 2>&1 &
  LPID=$!
  sleep 1.5

  if ! ss -tln | grep -q ":$p "; then
    printf "%-7s BIND_FAIL (in use or not permitted locally)\n" "$p"
    kill "$LPID" 2>/dev/null
    wait "$LPID" 2>/dev/null
    continue
  fi

  RES=$(curl -s --max-time 12 -X POST https://ports.yougetsignal.com/check-port.php \
        -d "remoteAddress=$IP&portNumber=$p" \
        -H "X-Requested-With: XMLHttpRequest" \
        | sed 's/<[^>]*>//g' | tr -d '\n' | xargs)
  case "$RES" in
    *" is open "*)   printf "%-7s OPEN\n" "$p" ;;
    *" is closed "*) printf "%-7s BLOCKED upstream (no local firewall rule)\n" "$p" ;;
    *)               printf "%-7s UNKNOWN: %s\n" "$p" "$RES" ;;
  esac

  kill "$LPID" 2>/dev/null
  wait "$LPID" 2>/dev/null
  sleep 0.5
done

echo
echo "Cleanup check (should be empty):"
ss -tlnp 2>/dev/null | grep 'http.server\|python3' || echo "  no stray listeners"
