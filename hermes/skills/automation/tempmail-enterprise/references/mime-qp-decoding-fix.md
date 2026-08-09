# MIME/Quoted-Printable Email Parser Fix

## Problem
Emails stored with raw MIME content. Magic links show `=3D` instead of `=`. URLs broken by `=\r\n` soft line breaks. Frontend renders raw HTML/CSS code. Buttons with `mso-hide:all` invisible.

## Root Causes (multiple)
1. Backend's `clean_mime_body()` NOT called before storing
2. QP decoder matched lowercase hex → corrupted data (`=edge` → 0xED)
3. Email handler v2 used `sed`+`tr` which broke complex HTML with conditional comments
4. Frontend stripped ALL conditional comments including `<!--[if !mso]>` which contains the actual button
5. `mso-hide:all` inline style hid buttons from non-Outlook browsers

## Backend Changes (email_parser.cpp)

### QP decoder — UPPERCASE HEX ONLY:
```cpp
// CRITICAL: only match uppercase hex (A-F) to prevent corruption
char h1 = input[i+1], h2 = input[i+2];
bool isHex = ((h1>='0'&&h1<='9')||(h1>='A'&&h1<='F')) &&
             ((h2>='0'&&h2<='9')||(h2>='A'&&h2<='F'));
if (isHex) {
    std::string hex = input.substr(i+1, 2);
    char c = (char)std::stoi(hex, nullptr, 16);
    result.push_back(c);
    i += 2;
} else {
    result.push_back(input[i]); // NOT a QP sequence, keep as-is
}
```

### MIME boundary regex fix:
```
[0-9a-f]+ → [0-9a-zA-Z_+=/-]+
```

### server.cpp — before store_email:
```cpp
clean_html = quoted_printable_decode(clean_html);
clean_body = quoted_printable_decode(clean_body);

// Remove mso-hide from inline styles (unhides buttons)
while (clean_html.find("mso-hide") != std::string::npos) {
    auto pos = clean_html.find("mso-hide");
    auto end = clean_html.find(";", pos);
    if (end != std::string::npos) clean_html.erase(pos, end - pos + 1);
    else clean_html.erase(pos);
}
```

## Email Handler v3 (send raw body)
v2 used `sed` + `tr '\n' ' '` which broke conditional comments. v3 sends raw body:
```bash
RAW_BODY=$(echo "$INPUT" | sed '1,/^$/d')
BODY_ESCAPED=$(echo "$RAW_BODY" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read())[1:-1])")
curl -s -X POST http://localhost:3001/api/incoming \
  -H "Content-Type: application/json" \
  -d "{\"from\":\"...\",\"to\":\"...\",\"subject\":\"...\",\"body\":\"$BODY_ESCAPED\",\"html\":\"\"}"
```

## Frontend Changes (page.tsx)

### extractHtmlFromMime — keep !mso content:
```typescript
function extractHtmlFromMime(raw: string): string {
  if (!raw) return '';
  let cleaned = raw.trim();
  cleaned = cleaned.replace(/<head>[\s\S]*?<\/head>/gi, '');
  cleaned = cleaned.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
  cleaned = cleaned.replace(/<img[^>]*(?:width="1"|height="1"|height:1px)[^>]*>/gi, '');
  // Strip MSO comments entirely (VML Outlook)
  cleaned = cleaned.replace(/<!--\[if\s*mso[^>]*>[\s\S]*?<!\[endif\]-->/gi, '');
  // Strip !mso DELIMITERS only — KEEP content (the actual <a> button)
  cleaned = cleaned.replace(/<!--\[if\s*!mso[^>]*><!--\s*>?/gi, '');
  cleaned = cleaned.replace(/<!--\s*<!\[endif\]-->/gi, '');
  // Strip remaining conditional comments
  cleaned = cleaned.replace(/<!--\[if\s*lte[^>]*>[\s\S]*?\[endif\]-->/gi, '');
  cleaned = cleaned.replace(/<!--\[if[^>]*>[\s\S]*?<!\[endif\]-->/gi, '');
  // Remove mso-hide and fix small heights
  cleaned = cleaned.replace(/mso-hide:\s*all[^;]*;?/gi, '');
  cleaned = cleaned.replace(/height:\s*17px/gi, 'height: auto');
  // Remove VML namespace tags
  cleaned = cleaned.replace(/<\/?[vw]:[^>]*>/gi, '');
  return cleaned.trim();
}
```

### CSS overrides for button visibility:
```css
.email-html-content [style*="mso-hide"] { display: block !important; visibility: visible !important; height: auto !important; }
.email-html-content a[style*="background"] { display: inline-block !important; height: auto !important; min-height: 40px; visibility: visible !important; }
.email-html-content .default-button, .email-html-content [data-btn] { display: inline-block !important; height: auto !important; min-height: 40px; visibility: visible !important; }
```

## Critical Pitfalls
1. **NEVER decode QP twice** — once in backend OR frontend, NOT both
2. **QP decoder must only match uppercase hex** — lowercase causes corruption
3. **Strip `<!--[if !mso]>` delimiters but KEEP content** — modern browsers treat as HTML comments
4. **Strip `mso-hide:all` from inline styles** — hides buttons from non-Outlook
5. **Send raw body in email handler** — sed/tr breaks conditional comments
