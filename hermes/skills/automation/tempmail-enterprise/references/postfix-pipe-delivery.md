# Postfix Pipe Delivery — Troubleshooting Flow

## Symptom: Emails stuck in queue, not reaching handler

```bash
mailq                    # Shows queued messages
postqueue -f             # "Cannot flush - mail system is down" → Postfix master stuck
tail -20 /var/log/mail.log | grep pipe   # No pipe entries
```

## Diagnosis steps

### 1. Check pipe transport config
```bash
grep tempmail /etc/postfix/master.cf
# Should show: tempmail unix - n n - 10 pipe
#              flags=q user=admin argv=/usr/local/bin/tempmail-handler ...
```

### 2. Check flags
- `flags=Rq` → `fatal: invalid option: R` on Postfix 3.6.x (Ubuntu 22.04)
- Fix: `flags=q`

### 3. Check user permissions
- `user=root` → Postfix rejects (security)
- `user=nobody` → Can't write to `/var/mail/admin` (Permission denied)
- `user=admin` → Works if admin owns `/var/mail/admin`

### 4. Check transport map
```bash
cat /etc/postfix/transport
# routerssh.web.id tempmail:
postmap -q "routerssh.web.id" hash:/etc/postfix/transport
# Should return: tempmail:
```

### 5. Check handler directly
```bash
echo "Subject: Test\nFrom: test@test.com\nTo: golem@domain\n\nBody" | /usr/local/bin/tempmail-handler
echo $?
cat /var/mail/admin | tail -10
```

### 6. Queue stuck fix (nuclear)
```bash
postfix stop
sleep 2
killall -9 master       # Force kill stuck master
sleep 1
postsuper -d ALL        # Clear all queued messages
postfix start
sleep 3
postfix status           # Should say "running"
ss -tlnp | grep :25     # Should show master listening
```

## Root cause patterns

| Symptom | Cause | Fix |
|---------|-------|-----|
| `fatal: invalid option: R` | flags=Rq not supported | flags=q |
| `user=root` rejected | Postfix security | user=admin |
| `Permission denied` on mbox | user=nobody can't write | user=admin |
| `mail system is down` on flush | Master process stuck | killall -9 master + restart |
| Emails in queue, no pipe logs | Transport not routing | Check transport_maps + domain in mydestination |
| Local sendmail works, external doesn't | Port 25 blocked by VPS | Cloudflare Email Routing |
