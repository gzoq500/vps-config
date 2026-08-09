---
name: vps-migration-handover
description: Pack agent memory, project scripts, secrets/keystores, and systemd units into a single tarball and SSH-transfer to a new VPS so the next Hermes session can continue without re-discovery. Use when user asks to backup/migrate/pindah VPS.
triggers:
  - pindah vps
  - migrate vps
  - backup memory
  - handover server
  - transfer scripts ssh
  - kezem_vps_transfer
---

# VPS Migration + Handover Pack

When the user says work is moving to a new VPS, produce a **single archive** with memory + code + configs so the next agent does not re-learn the stack.

## User expectations (this user)

- **One or two clear archives**, not a pile of ad-hoc copies
- Include **agent memory** (who user is + project state), not only scripts
- When asked "memori + skill": pack the **full Hermes skills tree** (`~/.hermes/skills/`), not just MEMORY.md
- Include **README/HANDOVER** + a **paste-ready restore prompt** for Hermes on the new VPS
- SSH with password often; use **paramiko** if `sshpass` unavailable
- After transfer: extract + place files, report remote layout
- **Do not force-overwrite** live `config.yaml` / `.env` / `auth.json` — put them in a backup dir unless missing

## Pack layout (standard)

Two archives recommended:

1. `kezem_vps_transfer.tar.gz` — project scripts + secrets + handover
2. `kezem_hermes_memory_skills.tar.gz` — Hermes memories + skills + plugins

```text
vps_transfer_pack/
├── README_THIS.md
├── memory/
├── scripts/
├── mimo_scripts/
├── mysterium/
├── 9router/
└── config/

hermes_transfer/
├── RESTORE.md
├── memories/
├── skills/
├── plugins/
├── cron/
└── config/
```

## Build steps

```bash
# Project pack
mkdir -p /root/vps_transfer_pack/{memory,scripts,config,mysterium,9router}
cp /root/.hermes/memories/MEMORY.md /root/vps_transfer_pack/memory/ 2>/dev/null || true
cp /root/.hermes/memories/USER.md /root/vps_transfer_pack/memory/ 2>/dev/null || true
cp /root/HANDOVER.md /root/vps_transfer_pack/memory/ 2>/dev/null || true
cp /root/*.py /root/vps_transfer_pack/scripts/ 2>/dev/null || true
cp /root/*_vpn.sh /root/vps_transfer_pack/scripts/ 2>/dev/null || true
cp -a /root/.mysterium/keystore /root/vps_transfer_pack/mysterium/ 2>/dev/null || true
cp -a /root/.9router/jwt-secret /root/vps_transfer_pack/9router/ 2>/dev/null || true
cp -a /root/.9router/db /root/vps_transfer_pack/9router/ 2>/dev/null || true
cp /etc/systemd/system/9router.service /root/vps_transfer_pack/config/ 2>/dev/null || true
cd /root && tar -czf /root/kezem_vps_transfer.tar.gz vps_transfer_pack

# Hermes memory + skills pack
mkdir -p /root/hermes_transfer/{memories,skills,plugins,config,cron}
cp -a /root/.hermes/memories/. /root/hermes_transfer/memories/
cp -a /root/.hermes/skills/. /root/hermes_transfer/skills/
cp -a /root/.hermes/plugins/. /root/hermes_transfer/plugins/ 2>/dev/null || true
cp -a /root/.hermes/cron/. /root/hermes_transfer/cron/ 2>/dev/null || true
cp /root/.hermes/config.yaml /root/hermes_transfer/config/ 2>/dev/null || true
cp /root/.hermes/.env /root/hermes_transfer/config/env.hermes 2>/dev/null || true
cp /root/.hermes/auth.json /root/hermes_transfer/config/ 2>/dev/null || true
cd /root && tar -czf /root/kezem_hermes_memory_skills.tar.gz hermes_transfer
```

## Transfer (paramiko pattern)

```python
import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, port=22, username="root", password=pw, timeout=20)
sftp = client.open_sftp()
sftp.put("/root/kezem_vps_transfer.tar.gz", "/root/kezem_vps_transfer.tar.gz")
# remote extract + place files
client.exec_command("cd /root && tar -xzf kezem_vps_transfer.tar.gz && ...")
```

If `sshpass` missing and apt mirrors broken, **paramiko is the reliable path**.

## Remote place (after extract)

```bash
mkdir -p /root/mimo_scripts /root/.mysterium/keystore /root/.9router
cp -a /root/vps_transfer_pack/scripts/* /root/
cp -a /root/vps_transfer_pack/memory/* /root/mimo_scripts/
cp /root/vps_transfer_pack/README_THIS.md /root/README_HANDOVER.md
# keystores, 9router data, systemd units as needed
```

## Remote restore of Hermes skills

```bash
cd /root && tar -xzf kezem_hermes_memory_skills.tar.gz
H=/root/.hermes
mkdir -p "$H/memories" "$H/skills" "$H/plugins" "$H/cron"
cp -a /root/hermes_transfer/memories/. "$H/memories/"
cp -a /root/hermes_transfer/skills/. "$H/skills/"
cp -a /root/hermes_transfer/plugins/. "$H/plugins/" 2>/dev/null || true
mkdir -p /root/hermes_config_backup
cp -a /root/hermes_transfer/config/. /root/hermes_config_backup/
chmod 600 "$H/memories/MEMORY.md" "$H/memories/USER.md" 2>/dev/null || true
find "$H/skills" -name 'SKILL.md' | wc -l   # expect ~80+
```

## Handover message for next agent

Give a **copy-paste prompt** for Hermes on the new VPS:

```text
Kezem, restore state server baru.
Baca: /root/README_HANDOVER.md, /root/RESTORE_HERMES.md,
/root/.hermes/memories/MEMORY.md, /root/.hermes/memories/USER.md
Pastikan memory+skills aktif (~88 SKILL.md), script project di /root,
9router data di /root/.9router. Extract packs if missing.
Jangan overwrite config/auth sembarangan. Laporkan status singkat.
```

## Pitfalls

1. Don't pack multi-GB caches (node_modules, Chrome, Docker images) unless asked. Skills tree (~2–8MB) is fine.
2. Do pack durable project secrets (keystore, jwt) — user expects continuity.
3. Write both MEMORY and HANDOVER — memory alone is not enough for a cold agent.
4. Confirm remote free disk/RAM after connect before heavy reinstalls.
5. Prefer `kezem_vps_transfer.tar.gz` + `kezem_hermes_memory_skills.tar.gz`.
6. User may ask only for "memori + skill" after project pack already landed — still produce/restore the second archive.
7. Never blindly overwrite target `config.yaml` / `.env` / `auth.json`.
8. User may later cancel new-VPS install if **current host 9Router is enough** — do not force reinstall on target after packs already landed.
9. For 9Router continuity, pack **full providerConnections** (Inferhub + xiaomi-mimo OI keys), not just jwt-secret.
10. **sshpass with special characters** — use env var: `export SSHPASS='password' && sshpass -e ssh ...`. Inline quoting (`sshpass -p 'pass@'`) fails when shell expands special chars.
11. **Hermes-only migration (no 9Router).** When user says "hermes nya saja": tar `~/.hermes/skills/` + `~/.hermes/memories/` + `~/.hermes/config.yaml`. Sanitize API keys before transfer (`sed 's/api_key: sk-.*/api_key: YOUR_API_KEY_HERE/g'`). Install Hermes on target first (`curl -fsSL ... | bash`), then extract tar. Update `base_url` in config to point to correct 9Router IP. Skills count should match source (~80-97 SKILL.md files).
12. **SQL dump restore fails on fresh 9Router DB.** `sqlite3 $DB < backup.sql` returns errors on fresh install because schema is auto-created by 9Router on first request. Use Python `INSERT OR REPLACE` with explicit column mapping instead. See `9router` skill reference `fresh-reinstall-and-provider-restore.md`.
13. **Vision config on new VPS must use new 9Router's API key.** After transferring skills+memories, the `auxiliary.vision` section in config.yaml still points to old VPS's 9Router. Update both `base_url` (new IP) AND `api_key` (new 9Router's key from `apiKeys` table). Command: `hermes config set auxiliary.vision.base_url http://NEW_IP:20128/v1` + `hermes config set auxiliary.vision.api_key NEW_KEY`. If vision model uses a provider prefix (e.g., `xkiro/xiaomi/mimo-v2.5:free`), that provider must exist on the NEW 9Router — add it before testing vision.

## Related skills

- `xiaomi-account-automation` — MiMo project details inside pack
- `9router` — reinstall/ops router; Inferhub prefix, Hermes override, image-gen path
