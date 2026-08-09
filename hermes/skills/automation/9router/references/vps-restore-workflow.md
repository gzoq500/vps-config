# VPS Restore Workflow — Golem's Config

**Repo:** `https://github.com/gzoq500/vps-config`  
**Purpose:** One-command restore of entire VPS config (Hermes + 9Router + AgentRouter + system tuning) on a fresh Ubuntu/Debian VPS.

## What Gets Restored

| Component | Source File | Installed To |
|---|---|---|
| System packages | `install.sh` (inline) | apt-get |
| Swap 4GB | `fstab-swap-entry.txt` | `/swapfile` + `/etc/fstab` |
| Network tuning | `sysctl.conf` | `/etc/sysctl.conf` |
| 9Router | `9router.service` | `/etc/systemd/system/9router.service` |
| AgentRouter Proxy | `agentrouter-proxy.js` | `/root/agentrouter-proxy.js` |
| Hermes config | `hermes/config-template.yaml` | `/root/.hermes/config.yaml` |
| 9Router DB | `9router/9router-db-dump.sql` | `/root/.9router/db/data.sqlite` |

## One-Command Restore

```bash
curl -fsSL https://raw.githubusercontent.com/gzoq500/vps-config/main/restore.sh | bash
```

## Manual Steps After Restore

1. **Update API keys** (not stored in repo for security):
   ```bash
   # Hermes config
   hermes config set model.api_key <your-key>
   hermes config set auxiliary.vision.api_key <your-key>
   
   # 9Router DB — update provider API keys
   sqlite3 /root/.9router/db/data.sqlite "UPDATE providerConnections SET data=json_set(data,'$.apiKey','<new-key>') WHERE name='XKiro Main';"
   ```

2. **Open ports in VPS firewall** (UpCloud panel):
   - Port 8443 (9Router external)
   - Port 3389 (AgentRouter — optional, localhost-only recommended)

3. **Start services:**
   ```bash
   systemctl start 9router
   systemctl start agentrouter-proxy
   ```

## 9Router DB Restore (Manual)

If you only want to restore the 9Router database (providers + API keys):

```bash
mkdir -p /root/.9router/db
curl -fsSL https://raw.githubusercontent.com/gzoq500/vps-config/main/9router/9router-db-dump.sql | sqlite3 /root/.9router/db/data.sqlite
systemctl restart 9router
```

## AgentRouter Proxy Setup (Manual)

```bash
curl -fsSL https://raw.githubusercontent.com/gzoq500/vps-config/main/agentrouter-proxy.js -o /root/agentrouter-proxy.js
sed -i 's/const PORT = 20199;/const PORT = 3389;/' /root/agentrouter-proxy.js
curl -fsSL https://raw.githubusercontent.com/gzoq500/vps-config/main/agentrouter-proxy.service -o /etc/systemd/system/agentrouter-proxy.service
systemctl daemon-reload && systemctl enable --now agentrouter-proxy
```

## Verify After Restore

```bash
# 9Router
systemctl is-active 9router && ss -tlnp | grep 8443

# AgentRouter
systemctl is-active agentrouter-proxy && ss -tlnp | grep 3389

# Test model routing
curl -s http://localhost:8443/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <9router-key>" \
  -d '{"model":"orca/tencent/hy3","messages":[{"role":"user","content":"Hi"}],"max_tokens":10}'
```

## Notes

- **Swap:** Script checks if `/swapfile` exists before creating (won't overwrite).
- **API keys:** DB dump contains placeholder keys — update before use.
- **Port 3389:** AgentRouter proxy listens on `0.0.0.0:3389` by default. For security, change `const PORT = 3389` to `const PORT = 3389` and ensure firewall blocks external access — let 9Router route internally.
- **Temperature:** Hermes config sets `temperature: 0.0` for deterministic output (coding tasks).
