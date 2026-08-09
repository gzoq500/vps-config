# VPS Config — Kezem Setup

Backup lengkap konfigurasi VPS untuk restore cepat.

## Quick Start

```bash
# 1. Clone repo
git clone https://github.com/gzoq500/vps-config.git
cd vps-config

# 2. Edit config (ganti API keys)
nano hermes/config.yaml
nano configs/keelcode_proxy.py

# 3. Run setup
chmod +x scripts/setup.sh
sudo bash scripts/setup.sh
```

## Apa yang di-backup

### Config Files
| File | Fungsi |
|---|---|
| `hermes/config.yaml` | Hermes Agent config |
| `hermes/memories/MEMORY.md` | Kezem memory |
| `hermes/memories/USER.md` | User profile |
| `configs/adguard/AdGuardHome.yaml` | AdGuard Home config |
| `configs/unbound/custom.conf` | Unbound DNS recursive |
| `configs/caddy/Caddyfile` | Caddy reverse proxy |
| `configs/keelcode_proxy.py` | Keelcode proxy (4-token rotation) |
| `configs/systemd/*.service` | Systemd service files |
| `configs/iptables/rules.v4` | Firewall rules |

### Scripts
| Script | Fungsi |
|---|---|
| `scripts/setup.sh` | Full VPS setup (run once) |
| `scripts/patch_antigravity.sh` | Patch 9Router Antigravity (User-Agent + Google Search) |
| `scripts/adguard-cleanup.sh` | AdGuard auto-cleanup cron |

### Hermes Skills (50+ skills)
Semua skill Hermes termasuk:
- 9Router management
- Keelcode proxy
- Agent evaluation (NoHalu)
- Captcha solving
- Free AI API hunting
- TempMail enterprise
- Xiaomi account automation
- Dan banyak lagi...

## Arsitektur

```
Internet
  │
  ├── :443 (sslh) → SSH (:22) / HTTP (:80) / HTTPS (:4443)
  ├── :80 (caddy) → AdGuard Web UI
  ├── :53 (AdGuardHome) → DNS
  ├── :853 (AdGuardHome) → DoT (Private DNS)
  ├── :20128 (9router) → AI Model Router
  ├── :3456 (keelcode_proxy) → Keelcode Proxy
  │
  └── Internal
       ├── :5335 (unbound) → Recursive DNS → AdGuard upstream
       ├── :3000 (AdGuardHome) → Web UI
       └── :8443 (hermes) → Hermes Gateway
```

## Providers (9Router)

| Prefix | Provider | Models |
|---|---|---|
| `mimo/*` | Xiaomi MiMo | mimo-v2.5 (vision) |
| `ag/*` | Google Antigravity | 9 models (FREE!) |
| `kx/*` | Keelcode | 5 models |
| `qd/*` | Qoder | TBD |

## Antigravity Models (FREE)

| Model | Search | Reasoning |
|---|---|---|
| ag/gemini-3.6-flash-high | ✅ | ✅ |
| ag/gemini-pro-agent | ✅ | ✅ |
| ag/claude-sonnet-4-6 | ✅ | ✅ |
| ag/claude-opus-4-6-thinking | ✅ | ✅ |
| ag/gpt-oss-120b-medium | ✅ | ❌ |
| ag/gemini-3.1-pro-low | ✅ | ✅ |
| ag/gemini-3-flash-agent | ✅ | ❌ |
| ag/gemini-3.5-flash-low | ✅ | ❌ |
| ag/gemini-3-flash | ✅ | ❌ |

## After Setup Checklist

- [ ] Update API keys di `hermes/config.yaml`
- [ ] Login 9Router dashboard `http://IP:20128/dashboard`
- [ ] Add provider connections (xiaomi-mimo, antigravity, keelcode)
- [ ] Run `hermes setup`
- [ ] Run `bash scripts/patch_antigravity.sh` (setiap kali update 9router)
- [ ] Test: `curl http://localhost:20128/v1/models -H "Authorization: Bearer YOUR_KEY"`

## Restore dari Backup

```bash
# Copy dari repo ke sistem
cp hermes/config.yaml ~/.hermes/config.yaml
cp -r hermes/memories/* ~/.hermes/memories/
cp -r hermes/skills/* ~/.hermes/skills/
cp configs/keelcode_proxy.py /root/keelcode_proxy.py
cp configs/systemd/*.service /etc/systemd/system/
cp configs/adguard/AdGuardHome.yaml /opt/AdGuardHome/
cp configs/unbound/custom.conf /etc/unbound/unbound.conf.d/
cp configs/caddy/Caddyfile /etc/caddy/
cp scripts/*.sh /usr/local/bin/

systemctl daemon-reload
systemctl restart 9router AdGuardHome caddy unbound keelcode-proxy
```

## Port Reference

| Port | Service | Protocol |
|---|---|---|
| 22 | SSH | TCP |
| 53 | DNS (AdGuard) | UDP/TCP |
| 80 | HTTP (Caddy) | TCP |
| 443 | HTTPS/SSH (sslh) | TCP |
| 853 | DoT (AdGuard) | TCP |
| 3456 | Keelcode Proxy | TCP |
| 8443 | Hermes Gateway | TCP |
| 20128 | 9Router | TCP |
