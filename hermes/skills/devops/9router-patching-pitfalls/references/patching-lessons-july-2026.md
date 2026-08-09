# Patching Lessons from July 2026 Session

## Key Finding: Keepalive IIFE Patch IS the fix for "Recent Requests stuck"

The dashboard "Recent Requests" section only updates when:
1. `saveRequestUsage()` fires (only on `DONE` status, NOT on streaming abort)
2. EventEmitter `M` emits "update" event
3. SSE stream pushes new data to browser

Since Hermes uses streaming (most requests end as `ResponseAborted`), the "update" event rarely fires. The keepalive patch that sends `getUsageStats("today")` every 10 seconds IS the correct fix — it proactively pushes fresh data to the browser.

## What went wrong in this session (and how to avoid):

### Cascade failure pattern:
1. Patch 1 (keepalive) → works
2. Patch 2 (chunk 4884 filter) → works  
3. Patch 3 (ring buffer refresh) → causes subtle issues
4. Patch 4 (dynamic import) → crashes silently
5. Patch 5 (string replace in chunk) → SyntaxError
6. Revert → loses all patches

**Lesson:** Apply ONE patch at a time, verify it works, commit/push, then add the next. Never batch multiple patches to compiled minified JS.

### The working minimal patch set (proven):
1. **SSE route.js**: Replace `: ping` with IIFE that calls `BY("today")` (10s interval)
2. **Chunk 4884.js**: Change `return!1` to `return!0` in 0-token filter (2 occurrences)
3. **NO other patches** — everything else causes issues

### What NOT to patch:
- Chunk 4884.js Q() function (ring buffer init) — changing `!J.initialized` to `!0` causes flickering
- Chunk 4884.js U() function (saveRequestUsage) — any changes break token tracking
- SSE route.js rg() timeout wrapper — unnecessary if BY() timeout works
- Any dynamic import paths — crash silently in compiled chunks

### Backup strategy:
```bash
BACKUP="/root/9router-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP"
cp /usr/local/lib/node_modules/9router/app/.next-cli-build/server/app/api/usage/stream/route.js "$BACKUP/"
cp /usr/local/lib/node_modules/9router/app/.next-cli-build/server/chunks/4884.js "$BACKUP/"
```

### Ultimate restore:
```bash
npm uninstall -g 9router && npm install -g 9router
# Database preserved, all patches reverted
```
