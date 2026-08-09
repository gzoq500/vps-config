# AgentRouter Proxy Setup (gzoq500/vps-config)

## File
- Source: `https://github.com/gzoq500/vps-config/main/agentrouter-proxy.js`
- Installed: `/root/agentrouter-proxy.js`
- Port: **3389** (custom, changed from default 20199)
- Service: `agentrouter-proxy.service` (systemd, Restart=always)

## Fungsi
Proxy ke `agentrouter.org` dengan extra headers (X-Stainless-OS, User-Agent RooCode, dll) supaya request tidak di-block sebagai "unauthorized client".

## Endpoint
```
Base: http://95.111.195.148:3389/v1
Models: claude-opus-4-8, claude-opus-5, gpt-5.6-sol
```

## Masalah: Content Kosong
Response dari `gpt-5.6-sol` mengembalikan `"content":""` padahal `usage` menunjukkan token terpakai. Tidak konsisten.

Claude models (`claude-opus-5`) **tidak kena masalah ini** — content normal.

Kemungkinan penyebab:
- `prepareMessages()` di proxy terlalu agresif modifikasi system prompt
- `agentrouter.org` memperlakukan model OpenAI berbeda dari Anthropic

## Workaround
Gunakan model Claude lewat proxy ini, atau akses langsung via 9Router (`gorouter/claude-opus-5`).

## systemd service
```ini
[Unit]
Description=AgentRouter Header Proxy
After=network.target

[Service]
Type=simple
ExecStart=/root/.hermes/node/bin/node /root/agentrouter-proxy.js
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

## UpCloud Firewall
Port 3389 **harus dibuka manual** di UpCloud panel (bukan port standar). Kalau `ERR_CONNECTION_REFUSED` dari HP, cek panel UpCloud.
