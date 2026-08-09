---
name: tempmail
description: Manage tempmail system — temporary email service with SMTP/IMAP, web frontend, and C++ backend. Fix MIME decoding, link rendering, and email parsing issues.
triggers:
  - tempmail
  - temporary email
  - temp mail
  - disposable email
  - routermail
  - magic link
  - email verification
---

# TempMail System

## Architecture

- **Backend:** C++ server at `/opt/tempmail/backend/` (port 3001)
- **Frontend:** Next.js at `/opt/tempmail/frontend/` (port 3002)
- **SMTP/IMAP:** Postfix + Dovecot (ports 25, 993)
- **Services:** `tempmail-backend.service`, `tempmail-frontend.service`
- **Domain:** routerssh.web.id
- **Database:** `/opt/tempmail/backend/data/tempmail.db` (SQLite)

## Services & Health

```bash
systemctl status tempmail-backend tempmail-frontend
systemctl restart tempmail-backend tempmail-frontend

# Health check
curl http://localhost:3001/api/health
curl -o /dev/null -w "%{http_code}" http://localhost:3002
```

## Key Files

- Backend email parser: `/opt/tempmail/backend/src/email_parser.cpp`
- Backend header: `/opt/tempmail/backend/include/email_parser.h`
- Backend server: `/opt/tempmail/backend/src/server.cpp`
- Frontend page: `/opt/tempmail/frontend/src/app/page.tsx`
- Database: `/opt/tempmail/backend/data/tempmail.db`

## Rebuild Backend

```bash
cd /opt/tempmail/backend/build && cmake .. -DCMAKE_BUILD_TYPE=Release && make -j$(nproc)
systemctl restart tempmail-backend
```

## Rebuild Frontend

```bash
cd /opt/tempmail/frontend && npm run build
systemctl restart tempmail-frontend
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/alias` | POST | Create alias (random or custom email) |
| `/api/aliases` | GET | List active aliases |
| `/api/emails/<email>` | GET | Get emails for alias |
| `/api/email/<id>` | GET | Get specific email |
| `/api/check/<email>?after=<id>` | GET | Check for new emails |
| `/api/incoming` | POST | Receive email from Postfix |
| `/api/send` | POST | Send email via Postfix |
| `/api/alias/<email>` | DELETE | Delete alias |

## MIME Decoding — CRITICAL

### Root Cause: QP Decoder Too Aggressive

**BUG:** Using `stoi(hex, nullptr, 16)` on lowercase hex produces invalid UTF-8.
Example: `=edge` → `=ed` decoded as 0xED (invalid UTF-8) → JSON serialization crash → **HTTP 500**

**FIX:** Only decode UPPERCASE hex (0-9, A-F). Standard QP encoding always uses uppercase.

```cpp
// WRONG — decodes lowercase hex too
char c = (char)std::stoi(hex, nullptr, 16);

// CORRECT — only uppercase hex
char h1 = input[i+1], h2 = input[i+2];
bool isHex = ((h1>='0'&&h1<='9')||(h1>='A'&&h1<='F')) &&
             ((h2>='0'&&h2<='9')||(h2>='A'&&h2<='F'));
if (isHex) {
    char c = (char)std::stoi(input.substr(i+1, 2), nullptr, 16);
    result.push_back(c);
    i += 2;
} else {
    result.push_back(input[i]);  // literal '='
}
```

### When to Apply QP Decode

Apply `quoted_printable_decode()` **once** in `server.cpp` BEFORE `store_email()`. Do NOT apply twice (once in `clean_mime_body` + once explicitly) — double decode corrupts data.

```cpp
// In server.cpp, before store_email:
std::string clean_body = clean_mime_body(body);
std::string clean_html = html.empty() ? clean_body : clean_mime_body(html);
// Extract HTML from MIME if present
if (clean_body.find("Content-Type:") != std::string::npos) {
    std::string extracted_html = extract_html_body(body);
    if (!extracted_html.empty()) clean_html = extracted_html;
    std::string extracted_text = extract_text_body(body);
    if (!extracted_text.empty()) clean_body = extracted_text;
}
// ALWAYS decode QP once (handles =3D, soft breaks)
clean_html = quoted_printable_decode(clean_html);
clean_body = quoted_printable_decode(clean_body);
int id = db_.store_email(alias->id, from, to, subject, clean_body, clean_html);
```

### MIME Boundary Regex Fix

Old: `(?:--[0-9a-f]+|$)` — only matches hex boundaries
New: `(?:--[0-9a-zA-Z_+=/-]+|$)` — matches all valid MIME boundaries

### Function Declarations in Header

All decode functions must be declared in `email_parser.h`:
```cpp
std::string base64_decode(const std::string& input);
std::string quoted_printable_decode(const std::string& input);
std::string decode_content(const std::string& headers, const std::string& content);
std::string extract_html_body(const std::string& body);
std::string extract_text_body(const std::string& body);
std::string clean_mime_body(const std::string& body);
```

### Data Corruption Cleanup

If emails have invalid UTF-8 bytes (from old buggy QP decoder), fix with Python:

```python
import sqlite3, re
conn = sqlite3.connect("/opt/tempmail/backend/data/tempmail.db", detect_types=sqlite3.PARSE_DECLTYPES)
conn.text_factory = bytes  # Read as raw bytes to avoid crash
rows = conn.execute("SELECT id, body_html, body_text FROM emails").fetchall()
for row in rows:
    eid = row[0]
    html = row[1].decode('utf-8', errors='replace') if row[1] else ''
    text = row[2].decode('utf-8', errors='replace') if row[2] else ''
    clean_html = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', html).replace('\ufffd', '')
    clean_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text).replace('\ufffd', '')
    if clean_html != html or clean_text != text:
        conn.execute("UPDATE emails SET body_html=?, body_text=? WHERE id=?", (clean_html, clean_text, eid))
conn.commit()
```

**Key:** Use `conn.text_factory = bytes` to read corrupted data without crashing sqlite3.

## Frontend Rendering — CRITICAL

### extractHtmlFromMime Function (FINAL WORKING VERSION)

```typescript
function extractHtmlFromMime(raw: string): string {
  if (!raw) return '';
  let cleaned = raw.trim();
  cleaned = cleaned.replace(/<head>[\s\S]*?<\/head>/gi, '');
  cleaned = cleaned.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
  cleaned = cleaned.replace(/<img[^>]*(?:width="1"|height="1"|height:1px)[^>]*>/gi, '');
  cleaned = cleaned.replace(/<noscript>[\s\S]*?<\/noscript>/gi, '');
  cleaned = cleaned.replace(/<xml>[\s\S]*?<\/xml>/gi, '');
  // Strip MSO conditional comments entirely (VML blocks)
  cleaned = cleaned.replace(/<!--\[if\s*mso[^>]*>[\s\S]*?<!\[endif\]-->/gi, '');
  // Strip !mso delimiters, KEEP content inside
  cleaned = cleaned.replace(/<!--\[if\s*!mso[^>]*><!--\s*>?/gi, '');
  cleaned = cleaned.replace(/<!--\s*<!\[endif\]-->/gi, '');
  cleaned = cleaned.replace(/<!--\[if\s*lte[^>]*>[\s\S]*?\[endif\]-->/gi, '');
  cleaned = cleaned.replace(/<!--\[if[^>]*>[\s\S]*?<!\[endif\]-->/gi, '');
  cleaned = cleaned.replace(/\s*-->\s*/g, ' ');
  cleaned = cleaned.replace(/mso-hide:\s*all[^;]*;?/gi, '');
  cleaned = cleaned.replace(/height:\s*17px/gi, 'height: auto');
  cleaned = cleaned.replace(/<\/?[vw]:[^>]*>/gi, '');
  cleaned = cleaned.replace(/background-color:\s*#(?:fff|ffffff|faf9f5|f5f5f5|f2f4f6|f8f9fa|f0f0f0)[^;]*;?/gi, '');
  cleaned = cleaned.replace(/background:\s*#(?:fff|ffffff|faf9f5|f5f5f5|f2f4f6|f8f9fa|f0f0f0)[^;]*;?/gi, '');
  cleaned = cleaned.replace(/bgcolor=["'](?:#fff|#ffffff|#faf9f5|#f5f5f5)["']/gi, '');
  cleaned = cleaned.replace(/(background-color:\s*#[0-9a-f]+[^"]*color:)\s*#[0-9a-f]+/gi, '$1 #ffffff');
  return cleaned.trim();
}
```

### emailStyles CSS — NO INVALID SYNTAX

**PITFALL:** `<!--[if` in CSS selectors is INVALID CSS → breaks entire `<style>` tag → all email content renders as blank white box. This was the root cause of emails showing blank on mobile.

```typescript
const emailStyles = `
  .email-html-content { max-width: 100%; overflow-x: auto; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 14px; line-height: 1.6; color: #1a1a1a; }
  .email-html-content * { max-width: 100% !important; box-sizing: border-box; }
  .email-html-content img { max-width: 100% !important; height: auto !important; border-radius: 8px; }
  .email-html-content a { color: #2563eb !important; text-decoration: underline; word-break: break-all; }
  .email-html-content table { max-width: 100% !important; border-collapse: collapse; }
  .email-html-content td, .email-html-content th { max-width: 100% !important; word-wrap: break-word; overflow-wrap: break-word; padding: 4px 8px; }
  .email-html-content [style*="mso-hide"] { display: block !important; visibility: visible !important; height: auto !important; }
  .email-html-content a[style*="background"] { display: inline-block !important; height: auto !important; min-height: 40px; visibility: visible !important; }
  .email-html-content .default-button, .email-html-content [data-btn] { display: inline-block !important; height: auto !important; min-height: 40px; visibility: visible !important; }
  .email-html-content img[width="1"][height="1"], .email-html-content img[style*="height:1px"] { display: none !important; }
  .email-html-content noscript, .email-html-content xml { display: none !important; }
`;
```

**Key:** Last line uses `.email-html-content xml` NOT `.email-html-content <!--[if` — the latter is invalid CSS.

### Dark Theme UI

- Email card: `bg-gray-100 dark:bg-gray-800` header + 2×2 button grid
- Buttons: Change, Copy, Delete, Refresh in `bg-gray-800/80`
- Email content: white background card with rounded corners

### Change Email Modal

Input username + domain display + Random + Apply buttons.
Backend supports custom email: `POST /api/alias {"email": "custom@domain"}`

## mso-hide Removal (Outlook Buttons)

Buttons like "Confirm Email" in Gologin emails have `mso-hide:all` in inline styles — this hides them from non-Outlook clients too.

**Backend fix** — strip mso-hide before storing in `server.cpp`:
```cpp
// After QP decode, before store_email:
while (clean_html.find("mso-hide") != std::string::npos) {
    auto pos = clean_html.find("mso-hide");
    auto end = clean_html.find(";", pos);
    if (end != std::string::npos) clean_html.erase(pos, end - pos + 1);
    else clean_html.erase(pos);
}
```

**Frontend CSS override** (backup):
```css
.email-html-content [style*="mso-hide"] { display: block !important; visibility: visible !important; height: auto !important; }
```

## Conditional Comment Stripping — CRITICAL

Frontend must ONLY strip MSO/IE-specific comments, NOT `<!--[if !mso]>` which contains the actual clickable content:

```typescript
// WRONG — strips ALL conditional comments including !mso
.replace(/<!--[\\s\\S]*?-->/g, '')

// CORRECT — only strip MSO-specific, keep !mso content
.replace(/<!--\\[if\\s*mso[^>]*>[\\s\\S]*?<!\\[endif\\]-->/gi, '')
.replace(/<!--\\[if\\s*[^>]*IE[^>]*>[\\s\\S]*?<!\\[endif\\]-->/gi, '')
.replace(/<!--\\[if\\s*lte[^>]*>[\\s\\S]*?\\[endif\\]-->/gi, '')
.replace(/<!--\\[if\\s*!mso\\]><!-->/gi, '')
.replace(/<!--<!\\[endif\\]-->/gi, '')
```

## Email Handler v3 (Raw Body)

**v2 bug:** `sed` + `tr '\n' ' '` parsing broke complex HTML with conditional comments.

**v3 fix:** Send entire raw MIME body to backend, let C++ parser handle extraction:
```bash
#!/bin/bash
INPUT=$(cat)
FROM=$(echo "$INPUT" | grep -m1 "^From:" | sed 's/^From: //')
TO=$(echo "$INPUT" | grep -m1 "^To:" | sed 's/^To: //')
SUBJECT=$(echo "$INPUT" | grep -m1 "^Subject:" | sed 's/^Subject: //')
TO_EMAIL=$(echo "$TO" | grep -oP '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' | head -1 | tr '[:upper:]' '[:lower:]')
RAW_BODY=$(echo "$INPUT" | sed '1,/^$/d')
BODY_ESCAPED=$(echo "$RAW_BODY" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read())[1:-1])" 2>/dev/null)
curl -s -X POST http://localhost:3001/api/incoming \
  -H "Content-Type: application/json" \
  -d "{\"from\":\"$(echo \"$FROM\" | sed 's/\"/\\\\\"/g')\",\"to\":\"$TO_EMAIL\",\"subject\":\"$(echo \"$SUBJECT\" | sed 's/\"/\\\\\"/g')\",\"body\":\"$BODY_ESCAPED\",\"html\":\"\"}" 2>/dev/null
exit 0
```

## Frontend Linkify Helper

Auto-detect URLs in text body and make them clickable:
```typescript
function linkifyText(text: string): string {
  return text.replace(/(https?:\\/\\/[^\\s<>"']+)/g,
    '<a href="$1" target="_blank" rel="noopener noreferrer" style="color:#60a5fa;text-decoration:underline;word-break:break-all;">$1</a>');
}
```

## White Background Removal (Dark Theme)

Email HTML often has `background-color: #ffffff`, `#FFF`, `#F2F4F6` etc. which makes content **invisible** on dark theme containers (white text on white background = blank).

**Frontend fix in `extractHtmlFromMime`:**
```typescript
// Remove ALL light/white background colors
cleaned = cleaned.replace(/background-color:\s*#(?:fff|ffffff|faf9f5|f5f5f5|f2f4f6|f8f9fa|f0f0f0)[^;]*;?/gi, '');
cleaned = cleaned.replace(/background:\s*#(?:fff|ffffff|faf9f5|f5f5f5|f2f4f6|f8f9fa|f0f0f0)[^;]*;?/gi, '');
cleaned = cleaned.replace(/bgcolor=["'](?:#fff|#ffffff|#faf9f5|#f5f5f5)["']/gi, '');
```

## Height:17px Override

Outlook email buttons have `height: 17px` in inline styles which makes them tiny/invisible in modern browsers. Fix:
```typescript
cleaned = cleaned.replace(/height:\s*17px/gi, 'height: auto');
```

## Error Boundary in Email Rendering

Complex email HTML can crash `dangerouslySetInnerHTML`. Always wrap in try-catch:
```tsx
{(() => {
  try {
    const html = extractHtmlFromMime(email.body_html || '');
    if (html && html.trim().startsWith('<')) {
      return <div dangerouslySetInnerHTML={{ __html: html }} className="email-html-content" />;
    }
    // ... text fallback
  } catch (err) {
    const raw = email.body_text || email.body_html || '';
    return <div style={{whiteSpace:'pre-wrap'}}>{raw.substring(0, 2000)}</div>;
  }
})()}
```

## Random Button — Generate Locally

Previous implementation called `/api/alias` which created a new alias immediately. Fix: generate random Indonesian name + 3 chars locally in the input field:
```typescript
const handleRandom = () => {
  const names = ['andi','budi','citra','dewi','eko','fajar','gilang','hadi','indra','joko'];
  const name = names[Math.floor(Math.random() * names.length)];
  let suffix = '';
  for (let i = 0; i < 3; i++) suffix += 'abcdefghijklmnopqrstuvwxyz0123456789'[Math.floor(Math.random() * 36)];
  setUsername(name + suffix);
};
```

## Pitfalls

1. **QP decoder MUST only match uppercase hex.** Lowercase hex like `ed` from `=edge` produces invalid UTF-8 (0xED) → JSON crash → HTTP 500.
2. **Never apply QP decode twice.** `clean_mime_body` already decodes internally. Applying again after corrupts `=ab` patterns.
3. **SMTP pipe sends raw MIME** to `/api/incoming`. The `body` field contains full MIME content with headers, not just HTML.
4. **Use `conn.text_factory = bytes`** when reading corrupted SQLite data. Normal mode crashes on invalid UTF-8.
5. **Rebuild both backend AND frontend** after changes. Frontend changes need `npm run build`.
6. **Port 3002** is frontend (not 3000). Check `ss -tlnp` if unsure.
7. **auto_usage_log trigger** only fires for models matching `%grok%`, `%mimo%`, `%free%`.
8. **INVALID CSS `<!--[if` in emailStyles breaks ALL email rendering.** If `emailStyles` contains `<!--[if` (even as a CSS selector), the browser's CSS parser treats the entire `<style>` block as invalid → ALL email content renders as blank white/empty box. Root cause of "email body shows blank on mobile" bug. **NEVER include HTML comment syntax in CSS selectors.** Always use `.email-html-content xml` not `.email-html-content <!--[if`.
9. **`<!--[if !mso]>` is an HTML comment to modern browsers.** Content inside `<!--[if !mso]><!-->...<!--<![endif]-->` is treated as a comment and NOT rendered. The clickable `<a>` button for email verification is often inside this block. **Fix:** strip the comment delimiters but keep the content between them.
10. **White backgrounds make email content invisible.** Email HTML has `background-color:#FFF`, `#F2F4F6`, `#FAF9F5` etc. On a dark-theme container with white card, this creates white-on-white. Strip ALL light background colors in `extractHtmlFromMime`.
11. **`height:17px` on Outlook buttons makes them invisible.** Buttons like "Confirm Email" have `height:17px` in inline styles (meant for Outlook VML). Override to `height:auto`.
12. **Email handler v2 `tr '\n' ' '` breaks complex HTML.** The `sed`/`tr` parsing in v2 handler destroys multiline HTML with conditional comments. **Always use v3** which sends raw MIME body to backend and lets C++ parser handle extraction.
13. **Root cause of blank email body: invalid CSS `<!--[if` in emailStyles.** The `emailStyles` template literal contained `.email-html-content <!--[if { display: none !important; }` — the `<!--[if` is NOT valid CSS and breaks the ENTIRE `<style>` tag. This was the root cause of ALL emails rendering as blank white boxes on mobile. **Fix:** Remove the `<!--[if` selector entirely.
14. **Table elements collapse to zero height.** Email HTML from services like Capsolver uses `<table>` with `bgcolor="#FFF"` and nested tables. When rendered inside a React `<div>` with `overflow: hidden`, the table collapses to 0px height. **Fix:** Add CSS overrides for `display: table !important` on tables and `display: revert !important` on cells.
15. **Frontend rendering: strip HTML tags for maximum reliability.** For complex email HTML (tables, conditional comments, VML), the safest approach is to strip ALL HTML tags and render as plain text with clickable URLs. Use: `raw.replace(/<[^>]*>/g, '')` then `linkifyText()`. This avoids ALL table collapse, conditional comment, and CSS issues.
16. **Backend `clean_mime_body()` must be called BEFORE `store_email()`.** The stock code stores raw MIME content directly. Apply `clean_mime_body()` + `quoted_printable_decode()` + `mso-hide` stripping BEFORE the INSERT.
17. **Random button generates locally, not via API.** Previous implementation called `/api/alias` which created a new alias immediately. Generate random Indonesian name + 3 chars locally in the input field.
18. **UTF-8 sanitization for corrupted data.** Use `conn.text_factory = bytes` + `.decode('utf-8', errors='replace')` when reading. Clean with `re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', html)`.
