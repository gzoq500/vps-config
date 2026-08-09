#!/bin/bash
set -e

# ============================================
# VPS Full Setup Script
# Target: Ubuntu 22.04+ / 2vCPU / 4GB RAM
# By: Kezem for Golem
# ============================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err() { echo -e "${RED}[-]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# ============================================
# STEP 1: SYSTEM BASE
# ============================================
log "Step 1: System base setup..."

# Disable unnecessary services
systemctl disable --now snapd snapd.socket 2>/dev/null || true
systemctl disable --now multipathd 2>/dev/null || true
systemctl disable --now packagekit 2>/dev/null || true
systemctl disable --now unattended-upgrades 2>/dev/null || true
systemctl mask systemd-resolved 2>/dev/null || true
systemctl stop systemd-resolved 2>/dev/null || true

# Swap (auto by RAM)
if [ ! -f /swapfile ]; then
    RAM_MB=$(free -m | awk '/Mem:/ {print $2}')
    if [ "$RAM_MB" -le 2048 ]; then
        SWAP_MB=4096
    elif [ "$RAM_MB" -le 4096 ]; then
        SWAP_MB=8192
    else
        SWAP_MB=$((RAM_MB * 2))
    fi
    log "Creating ${SWAP_MB}MB swap..."
    fallocate -l ${SWAP_MB}M /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# Journal limit
mkdir -p /etc/systemd/journald.conf.d/
cat > /etc/systemd/journald.conf.d/limit.conf << 'EOF'
[Journal]
SystemMaxUse=50M
RuntimeMaxUse=50M
EOF
systemctl restart systemd-journald

# Install base packages
apt-get update -qq
apt-get install -y -qq curl wget git sqlite3 jq net-tools certbot

log "Step 1 done!"

# ============================================
# STEP 2: DNS (AdGuard Home + Unbound)
# ============================================
log "Step 2: DNS setup..."

# Install Unbound
apt-get install -y -qq unbound

# Unbound config
cp "$SCRIPT_DIR/configs/unbound/custom.conf" /etc/unbound/unbound.conf.d/custom.conf
systemctl enable --now unbound
systemctl restart unbound

# Install AdGuard Home
if [ ! -f /opt/AdGuardHome/AdGuardHome ]; then
    curl -sSL https://github.com/AdguardTeam/AdGuardHome/releases/latest/download/AdGuardHome_linux_amd64.tar.gz | tar xz -C /opt/
    /opt/AdGuardHome/AdGuardHome -s install
fi

# Restore AdGuard config
cp "$SCRIPT_DIR/configs/adguard/AdGuardHome.yaml" /opt/AdGuardHome/AdGuardHome.yaml
systemctl restart AdGuardHome

# AdGuard cleanup cron
cp "$SCRIPT_DIR/scripts/adguard-cleanup.sh" /usr/local/bin/adguard-cleanup.sh
chmod +x /usr/local/bin/adguard-cleanup.sh
(crontab -l 2>/dev/null; echo "0 3 * * * /usr/local/bin/adguard-cleanup.sh >> /var/log/adguard-cleanup.log 2>&1") | crontab -

log "Step 2 done!"

# ============================================
# STEP 3: REVERSE PROXY (Caddy)
# ============================================
log "Step 3: Caddy setup..."

if ! command -v caddy &>/dev/null; then
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -qq
    apt-get install -y -qq caddy
fi

cp "$SCRIPT_DIR/configs/caddy/Caddyfile" /etc/caddy/Caddyfile
systemctl enable --now caddy
systemctl restart caddy

log "Step 3 done!"

# ============================================
# STEP 4: SSLH (SSH+HTTPS multiplexer)
# ============================================
log "Step 4: SSLH setup..."

apt-get install -y -qq sslh
cat > /etc/sslh.cfg << 'EOF'
verbose: false;
foreground: false;
timeout: 5;
user: "sslh";
listen:
    ({ host: "0.0.0.0"; port: "443"; });
protocols:
    ({ name: "ssh"; service: "ssh"; host: "127.0.0.1"; port: "22"; },
     { name: "http"; host: "127.0.0.1"; port: "80"; },
     { name: "tls"; host: "127.0.0.1"; port: "4443"; });
EOF
systemctl enable --now sslh
systemctl restart sslh

log "Step 4 done!"

# ============================================
# STEP 5: IPTABLES
# ============================================
log "Step 5: Firewall rules..."

# Apply saved rules
if [ -f "$SCRIPT_DIR/configs/iptables/rules.v4" ]; then
    iptables-restore < "$SCRIPT_DIR/configs/iptables/rules.v4"
fi

# NAT for DoT (853 -> 8880)
iptables -t nat -A PREROUTING -p tcp --dport 853 -j REDIRECT --to-port 8880 2>/dev/null || true

# Save rules
mkdir -p /etc/iptables
iptables-save > /etc/iptables/rules.v4

log "Step 5 done!"

# ============================================
# STEP 6: NODE.JS + 9ROUTER
# ============================================
log "Step 6: 9Router setup..."

if ! command -v node &>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y -qq nodejs
fi

npm install -g 9router@latest

# 9Router systemd service
cat > /etc/systemd/system/9router.service << 'EOF'
[Unit]
Description=9Router AI Smart Router
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/9router --tray --skip-update -p 20128
Restart=always
RestartSec=5
WorkingDirectory=/root/.9router
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now 9router
sleep 15

# Patch antigravity User-Agent + Google Search
bash "$SCRIPT_DIR/scripts/patch_antigravity.sh" 2>/dev/null || true
systemctl restart 9router

log "Step 6 done!"

# ============================================
# STEP 7: KEELCODE PROXY
# ============================================
log "Step 7: Keelcode proxy setup..."

pip3 install anthropic requests

cp "$SCRIPT_DIR/configs/keelcode_proxy.py" /root/keelcode_proxy.py
cp "$SCRIPT_DIR/configs/systemd/keelcode-proxy.service" /etc/systemd/system/keelcode-proxy.service

systemctl daemon-reload
systemctl enable --now keelcode-proxy

log "Step 7 done!"

# ============================================
# STEP 8: HERMES AGENT
# ============================================
log "Step 8: Hermes setup..."

if ! command -v hermes &>/dev/null; then
    curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
fi

# Restore config
mkdir -p /root/.hermes
cp "$SCRIPT_DIR/configs/hermes/config.yaml" /root/.hermes/config.yaml

# Restore skills
if [ -d "$SCRIPT_DIR/skills" ]; then
    mkdir -p /root/.hermes/skills
    cp -r "$SCRIPT_DIR/skills/"* /root/.hermes/skills/ 2>/dev/null || true
fi

systemctl enable --now hermes-gateway 2>/dev/null || true

log "Step 8 done!"

# ============================================
# STEP 9: VERIFY
# ============================================
log "Step 9: Verification..."

echo ""
echo "=========================================="
echo "  SERVICE STATUS"
echo "=========================================="

for svc in 9router AdGuardHome caddy unbound keelcode-proxy sslh; do
    status=$(systemctl is-active $svc 2>/dev/null || echo "not found")
    if [ "$status" = "active" ]; then
        echo -e "  ${GREEN}✅${NC} $svc: $status"
    else
        echo -e "  ${RED}❌${NC} $svc: $status"
    fi
done

echo ""
echo "=========================================="
echo "  PORTS"
echo "=========================================="
ss -tlnp | grep -E ':(22|53|80|443|3456|8443|20128|853|8880)\s' | awk '{print "  " $4 " -> " $6}'

echo ""
echo "=========================================="
echo "  RESOURCE USAGE"
echo "=========================================="
echo "  RAM: $(free -h | awk '/Mem:/ {print $3 "/" $2}')"
echo "  Disk: $(df -h / | awk 'NR==2 {print $3 "/" $2}')"
echo "  Load: $(uptime | awk -F'load average:' '{print $2}')"

echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}  SETUP COMPLETE!${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo "  9Router Dashboard: http://YOUR_IP:20128/dashboard"
echo "  AdGuard Home:      http://YOUR_IP:80"
echo "  DNS:               YOUR_IP:53"
echo "  Hermes Gateway:    port 8443"
echo ""
echo "  Next steps:"
echo "  1. Login to 9Router dashboard (default: admin/admin)"
echo "  2. Add API providers (xiaomi-mimo, antigravity, keelcode)"
echo "  3. Run: hermes setup"
echo "  4. Update API keys in config.yaml"
echo ""
