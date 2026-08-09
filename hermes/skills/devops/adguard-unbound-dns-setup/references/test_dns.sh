#!/bin/bash
# Test DNS speed for AdGuard + Unbound setup
echo "=== DNS Speed Test ==="
echo "Cached domain (google.com):"
dig @127.0.0.1 google.com +stats | grep "Query time"

echo "New domain (instagram.com):"
dig @127.0.0.1 instagram.com +stats | grep "Query time"

echo "New domain (github.com):"
dig @127.0.0.1 github.com +stats | grep "Query time"

echo "=== Ping Test ==="
ping -c 5 127.0.0.1 | tail -3
