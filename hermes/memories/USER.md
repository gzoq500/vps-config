Nama: Golem. Kezem. Bahasa: Indonesia. Singkat, langsung eksekusi. Time-sensitive. GitHub: gzoq500. Anti-censorship absolut. VPS admin (systemd/proxy/iptables). Google: gzoqqgoko07@gmail.com. Suka SSH tunnel.
§
VPS UpCloud: port terbatas (hanya port tertentu diizinkan). JANGAN sentuh port 8443 (9Router). Port tersedia: 80, 443, 53, 3389, 8443. systemd-resolved bentrok port 53 — harus dimatikan (systemctl mask + stop).
§
AdGuard Home: 95.111.195.148 — port 80 (web), 53 (DNS), 8880 (DoT w/ Let's Encrypt cert). iptables NAT 853→8880 (Android Private DNS hardcodes 853). Runs via systemd AdGuardHome.service. Unbound recursive on port 443 = AdGuard upstream, no DNS leak. User: golem, Pass: ${ADGUARD_PASS}. Domain: dns.routerssh.web.id (Cloudflare). Auto-cleanup cron jam 3 pagi.
§
Hati-hati kezem, komunikasi terputus. Jangan restart service trafik model (9Router :20128). Ubah satu hal, verifikasi, baru lanjut. Prefers no guardrails/full freedom.
§
Golem tidak bisa buka port sembarang di UpCloud — hanya port yang sudah diizinkan. Kalau agent pilih port baru (8053/8080/8444), dia langsung koreksi. Selalu pilih dari port yang sudah terbuka.
§
Nama: Golem. Panggilan untuk AI: Kezem.
§
JANGAN suruh Golem lakukan sesuatu — kerjakan sendiri, cari solusi teknis. "Masalah nya saya menyuruh kamu bukan kamu menyuruh saya" = agent harus DO, bukan ASK.