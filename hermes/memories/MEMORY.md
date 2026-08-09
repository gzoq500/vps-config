Golem. Panggilan agen: Kezem. Bahasa Indonesia. Concise, langsung eksekusi. Technical, "bebas" (free/unrestricted). Deep benchmarking > one-off tests. No guardrails.
§
Host: YOUR_VPS_IP Buffalo NY 2vCPU EPYC/3.8GB/49GB. DNS: AdGuard+Unbound+Caddy. dns.routerssh.store. Speed ~341/898 Mbit/s.
§
Keelcode proxy: port 3456 (systemd keelcode-proxy.service), OpenAI→Anthropic for keelcode.ai. Models: kx/kimi-k3 (10 req/hari), kx/deepseek-v4-flash, kx/deepseek-v4-pro, kx/kimi-k2.6, kx/kimi-k2.7-code. 4 tokens in rotation (/root/.keelcode_tokens.json), auto-rotate on 429. Tokens from accounts: tiranda, sopian, diana, fitri @bukitsakura.com. Proxy script: /root/keelcode_proxy.py.
§
VCC/CC Golem selalu ditolak AWS/Kiro. Tidak bisa beli subscription yang butuh kartu. Fokus cari akses gratis (free tier, trial, :free models).
§
TempMail: C++ :3001, Next.js :3002. Repo: gzoq500/tempmail-enterprise. Hermes vYOUR_VPS_IP 9Router vYOUR_VPS_IP
§
GitHub backup: gzoq500/vps-config (token ${GITHUB_TOKEN}). Isi: restore.sh (swap auto by RAM), 9router-db-dump.sql, hermes config (approvals.mode=off = no approval dialog), adguard+unbound configs, iptables rules, skills, memories. Restore: curl -fsSL https://raw.githubusercontent.com/gzoq500/vps-config/main/restore.sh | bash — lalu update API keys.
§
JANGAN PERNAH matikan 9Router (systemctl stop/restart 9router) — Hermes hidup dari sana (vision, model routing). Kalau mau update: install dulu npm i -g 9router@latest, BARU restart systemd. Jangan stop dulu.
§
Google Antigravity: WORKS via9Router (fixed Aug 2026). Root cause: User-Agent must be `Trae/1.0.0 antigravity-cockpit-tools` (patch compiled JS chunks 4963/5619/7011). OAuth: goxgavavo@gmail.com. 9 working models: ag/gemini-3.6-flash-high, ag/gemini-3-flash-agent, ag/gemini-pro-agent, ag/claude-sonnet-4-6, ag/claude-opus-4-6-thinking, ag/gpt-oss-120b-medium, ag/gemini-3.5-flash-low, ag/gemini-3.1-pro-low, ag/gemini-3-flash. CLI: /root/.local/bin/agy. Google Search grounding: inject `{google_search:{}}` in chunk 8499.js. Auto-patch: `/root/patch_antigravity.sh`. Re-patch after 9Router npm update!