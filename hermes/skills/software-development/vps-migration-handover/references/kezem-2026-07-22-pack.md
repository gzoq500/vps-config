# Pack instance: kezem_vps_transfer (2026-07-22)

## Archive
- Host build: `/root/kezem_vps_transfer.tar.gz` (~51KB)
- Contents: memory (MEMORY/USER/HANDOVER), MiMo scripts, Mysterium keystore, 9Router jwt+db, systemd units

## Destinations
- Primary new: `root@45.130.164.191:22` (pass shared by user) — extracted to `/root/vps_transfer_pack/`, scripts to `/root/`, README `/root/README_HANDOVER.md`
- Earlier: `root@157.245.200.33` (`/root/mimo_scripts/`)
- Old: `43.167.12.204` (3.6GB, reboot risk under heavy browser)

## Resume phrase for next agent
> Baca `/root/README_HANDOVER.md` dan memory pack; restore facts; lanjut 9Router + MiMo.

## Include next time
- Always: MEMORY.md + USER.md + project HANDOVER
- Keystores user owns for continuity
- systemd units for long-running services (9router, captcha-solver)
- Exclude: multi-GB browser caches, docker images unless requested