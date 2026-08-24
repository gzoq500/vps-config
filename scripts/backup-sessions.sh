#!/bin/bash
# Backup Hermes state.db (sesi + pesan + memory) ke GitHub repo gzoq500/vps-config
# Jalankan manual: bash /root/vps-config/scripts/backup-sessions.sh
set -e
REPO_DIR="/root/vps-config"
DB="/root/.hermes/state.db"

cd "$REPO_DIR"
git checkout db-backup 2>/dev/null || true

# Checkpoint WAL agar DB konsisten
python3 -c "import sqlite3; db = sqlite3.connect('$DB'); db.execute('PRAGMA wal_checkpoint(TRUNCATE)'); db.close()"

mkdir -p hermes/db-backup
gzip -c "$DB" > hermes/db-backup/state.db.gz

STAMP=$(date -u +"%Y-%m-%d %H:%M UTC")
SESSIONS=$(python3 -c "import sqlite3; print(sqlite3.connect('$DB').execute('SELECT COUNT(*) FROM sessions').fetchone()[0])")
MESSAGES=$(python3 -c "import sqlite3; print(sqlite3.connect('$DB').execute('SELECT COUNT(*) FROM messages').fetchone()[0])")

git add hermes/db-backup/state.db.gz
git commit -m "backup: state.db @ $STAMP ($SESSIONS sesi, $MESSAGES pesan)" || { echo "Tidak ada perubahan."; exit 0; }
git push origin db-backup
echo "✅ Backup sukses: $STAMP | $SESSIONS sesi | $MESSAGES pesan"
