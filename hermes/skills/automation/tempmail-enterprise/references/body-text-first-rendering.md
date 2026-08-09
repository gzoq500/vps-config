# Body-Text-First Email Rendering

## Problem
Old emails (pre-fix) store raw HTML in `body_text`. New emails (post `strip_html_tags` fix) store clean text. Frontend must handle both.

## Backend: strip_html_tags() in email_parser.cpp

Add `strip_html_tags()` and `strip_style_blocks()` functions. In `server.cpp`, call BEFORE `store_email()`:

```cpp
clean_body = strip_html_tags(clean_body);
if (clean_html.find("<") != std::string::npos) {
    std::string stripped = strip_html_tags(clean_html);
    if (stripped.length() > clean_body.length()) clean_body = stripped;
}
```

Result: `body_html` = original HTML, `body_text` = clean readable text.

## Frontend: Detect and handle both old/new emails

```typescript
// In EmailDetail component
const text = email.body_text || '';
const hasHtml = text.includes('<') && (text.includes('<html') || text.includes('<body') || text.includes('<!DOCTYPE'));

let clean = text;
if (hasHtml) {
  // Old email: body_text contains raw HTML - strip it
  clean = text
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<head>[\s\S]*?<\/head>/gi, '')
    .replace(/<br\s*\//gi, '\n')
    .replace(/<\/p>/gi, '\n\n')
    .replace(/<\/div>/gi, '\n')
    .replace(/<tr[^>]*>/gi, '\n')
    .replace(/<[^>]*>/g, '')
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&nbsp;/g, ' ')
    .replace(/=\r?\n/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[ \t]{2,}/g, ' ')
    .replace(/\r/g, '')
    .trim();
}
if (clean && clean.length > 10) {
  const linked = linkifyText(clean.replace(/\n/g, '<br/>'));
  return <div dangerouslySetInnerHTML={{ __html: linked }} />;
}
return <div>(Kosong)</div>;
```

## Why NOT dangerouslySetInnerHTML with raw HTML
- `<table>` elements collapse to 0px in `display:block` containers
- `<!--[if mso]>` comments hide content from modern browsers
- `mso-hide:all` hides buttons
- Invalid CSS (`<!--[if`) breaks entire `<style>` tag
- White backgrounds (`bgcolor="#FFF"`) make content invisible

## Verified working (July 2026)
- Capsolver emails: "Confirm email" button text visible ✅
- Claude emails: magic links clickable ✅
- Gologin emails: verification content readable ✅
- Xiaomi emails: verification codes visible ✅
