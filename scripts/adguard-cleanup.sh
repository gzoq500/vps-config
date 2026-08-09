#!/bin/bash
# =============================================================
# AdGuard Home - Auto Cleanup Script
# Bersihkan query log & reset statistik secara otomatis
# Author: Kezem (for Golem)
# =============================================================

COOKIE="/tmp/adguard_cookie_$$"
LOG="/var/log/adguard-cleanup.log"
API="http://127.0.0.1:80"
USER="golem"
PASS="Kolor900@"

login() {
    curl -s -X POST "$API/control/login" \
        -H "Content-Type: application/json" \
        -d "{\"name\":\"$USER\",\"password\":\"$PASS\"}" \
        -c "$COOKIE" -o /dev/null -w "%{http_code}"
}

cleanup() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Memulai cleanup AdGuard Home..."

    LOGIN=$(login)
    if [ "$LOGIN" != "200" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] LOGIN GAGAL (HTTP $LOGIN)" | tee -a "$LOG"
        rm -f "$COOKIE"
        exit 1
    fi

    QL=$(curl -s -b "$COOKIE" -X POST "$API/control/querylog_clear" -o /dev/null -w "%{http_code}")
    SR=$(curl -s -b "$COOKIE" -X POST "$API/control/stats_reset" -o /dev/null -w "%{http_code}")

    rm -f "$COOKIE"

    RESULT="$(date '+%Y-%m-%d %H:%M:%S') querylog_clear=$QL stats_reset=$SR"
    echo "$RESULT" >> "$LOG"
    echo "[$RESULT] Cleanup selesai."
}

case "${1:-}" in
    --test)
        echo "Mode test - tidak benar-benar membersihkan"
        LOGIN=$(login)
        if [ "$LOGIN" = "200" ]; then
            echo "✅ Login berhasil (HTTP 200)"
            rm -f "$COOKIE"
        else
            echo "❌ Login gagal (HTTP $LOGIN)"
            rm -f "$COOKIE"
            exit 1
        fi
        ;;
    --status)
        login > /dev/null
        echo "=== Query Log Info ==="
        curl -s -b "$COOKIE" "$API/control/querylog_info" 2>/dev/null | python3 -m json.tool 2>/dev/null || \
            curl -s -b "$COOKIE" "$API/control/querylog_info"
        echo ""
        echo "=== Statistik ==="
        curl -s -b "$COOKIE" "$API/control/stats" 2>/dev/null | python3 -m json.tool 2>/dev/null || \
            curl -s -b "$COOKIE" "$API/control/stats"
        rm -f "$COOKIE"
        ;;
    --log)
        if [ -f "$LOG" ]; then
            tail -20 "$LOG"
        else
            echo "Log belum ada (belum pernah dijalankan)"
        fi
        ;;
    *)
        cleanup
        ;;
esac