#!/bin/bash
# Verify AdGuard Home DNS-over-TLS is actually reachable the way Android will use it.
#
# Usage: ./verify-dot.sh dns.example.com 95.111.195.148 8880
#
# Android's Private DNS field takes ONLY a hostname and always dials port 853.
# So the meaningful test is a DoT query through 853 (relying on the NAT redirect),
# not against the real listener port.
set -uo pipefail

HOST="${1:?hostname required, e.g. dns.example.com}"
IP="${2:?VPS public IP required}"
DOT_PORT="${3:-8880}"

fail=0
ok()   { printf '  \033[32mOK\033[0m   %s\n' "$1"; }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$1"; fail=1; }

echo "== 1. Hostname resolves to this VPS =="
resolved=$(dig @1.1.1.1 "$HOST" +short | head -1)
[ "$resolved" = "$IP" ] && ok "$HOST -> $IP" || bad "$HOST -> '${resolved:-nothing}' (expected $IP)"

echo "== 2. Listeners =="
for p in 53 80 "$DOT_PORT"; do
  ss -tlnp 2>/dev/null | grep -q ":$p " && ok "port $p listening" || bad "port $p NOT listening"
done

echo "== 3. TLS certificate is publicly trusted (self-signed => Android refuses) =="
tls=$(echo | timeout 8 openssl s_client -connect "$HOST:$DOT_PORT" -servername "$HOST" 2>&1)
grep -q "Verify return code: 0 (ok)" <<<"$tls" && ok "cert chain trusted" || bad "cert NOT trusted"
grep -qi "issuer=.*Let's Encrypt" <<<"$tls" && ok "issued by Let's Encrypt" \
  || printf '  NOTE issuer: %s\n' "$(grep -m1 'issuer=' <<<"$tls")"

echo "== 4. DoT query through port 853 (the Android path) =="
if command -v kdig >/dev/null 2>&1; then
  if kdig @"$IP" +tls +tls-hostname="$HOST" -p 853 github.com 2>&1 | grep -q "ANSWER SECTION"; then
    ok "DoT via 853 answered (NAT redirect 853 -> $DOT_PORT works)"
  else
    bad "DoT via 853 failed — check: iptables -t nat -L PREROUTING -n"
  fi
else
  bad "kdig missing — apt-get install -y knot-dnsutils"
fi

echo "== 5. Plain DNS on 53 still works =="
dig @"$IP" cloudflare.com +short | grep -qE '^[0-9]' && ok "plain 53 resolves" || bad "plain 53 broken"

echo "== 6. Renewal hook exists (cert renews ~90d; AdGuard reads it only at startup) =="
[ -x /etc/letsencrypt/renewal-hooks/deploy/restart-adguard.sh ] \
  && ok "deploy hook present" || bad "no deploy hook -> DoT will silently break after renewal"

echo
[ "$fail" -eq 0 ] && echo "ALL CHECKS PASSED" || echo "SOME CHECKS FAILED"
exit "$fail"
