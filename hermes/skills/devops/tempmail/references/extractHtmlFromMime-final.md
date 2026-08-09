# extractHtmlFromMime — Final Working Version

This is the complete `extractHtmlFromMime` function used in `page.tsx` that handles all known email formats correctly (Claude, Gologin, VMOSCloud, Xiaomi, capsolver, GitHub, etc.).

## Function

```typescript
function extractHtmlFromMime(raw: string): string {
  if (!raw) return '';
  let cleaned = raw.trim();
  // Remove head section
  cleaned = cleaned.replace(/<head>[\s\S]*?<\/head>/gi, '');
  // Remove style tags
  cleaned = cleaned.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
  // Remove tracking pixels
  cleaned = cleaned.replace(/<img[^>]*(?:width=\"1\"|height=\"1\"|height:1px)[^>]*>/gi, '');
  // Remove noscript/xml
  cleaned = cleaned.replace(/<noscript>[\s\S]*?<\/noscript>/gi, '');
  cleaned = cleaned.replace(/<xml>[\s\S]*?<\/xml>/gi, '');
  // Strip MSO conditional comments entirely (VML blocks)
  cleaned = cleaned.replace(/<!--\[if\s*mso[^>]*>[\s\S]*?<!\[endif\]-->/gi, '');
  // Strip !mso delimiters, KEEP content inside
  cleaned = cleaned.replace(/<!--\[if\s*!mso[^>]*><!--\s*>?/gi, '');
  cleaned = cleaned.replace(/<!--\s*<!\[endif\]-->/gi, '');
  // Strip lte mso comments
  cleaned = cleaned.replace(/<!--\[if\s*lte[^>]*>[\s\S]*?\[endif\]-->/gi, '');
  // Strip remaining IE conditional comments
  cleaned = cleaned.replace(/<!--\[if[^>]*>[\s\S]*?<!\[endif\]-->/gi, '');
  // Remove stray --> from partial comment stripping
  cleaned = cleaned.replace(/\s*-->\s*/g, ' ');
  // Remove mso-hide from inline styles
  cleaned = cleaned.replace(/mso-hide:\s*all[^;]*;?/gi, '');
  // Override small heights on buttons
  cleaned = cleaned.replace(/height:\s*17px/gi, 'height: auto');
  // Remove VML namespace tags
  cleaned = cleaned.replace(/<\/?[vw]:[^>]*>/gi, '');
  // Remove ALL light/white background colors (prevents white-on-white)
  cleaned = cleaned.replace(/background-color:\s*#(?:fff|ffffff|faf9f5|f5f5f5|f2f4f6|f8f9fa|f0f0f0)[^;]*;?/gi, '');
  cleaned = cleaned.replace(/background:\s*#(?:fff|ffffff|faf9f5|f5f5f5|f2f4f6|f8f9fa|f0f0f0)[^;]*;?/gi, '');
  // Force white text on buttons with background color
  cleaned = cleaned.replace(/(background-color:\s*#[0-9a-f]+[^"]*color:)\s*#[0-9a-f]+/gi, '$1 #ffffff');
  return cleaned.trim();
}
```

## What Each Step Fixes

| Step | Problem Solved |
|------|---------------|
| Strip `<head>` | Remove CSS that conflicts with app styling |
| Strip `<style>` | Remove class-based CSS (`.r14-r`, `.default-button`) |
| Strip tracking pixels | Remove 1x1 open-tracking images |
| Strip MSO comments | Remove Outlook VML blocks (not rendered in modern browsers) |
| Strip `!mso` delimiters | Keep content that was wrapped in `<!--[if !mso]><!-->` |
| Remove stray `-->` | Clean up artifacts from comment stripping |
| Remove `mso-hide` | Unhide buttons like "Confirm Email" that were hidden for non-Outlook |
| Override `height:17px` | Make tiny Outlook buttons visible |
| Remove VML tags | Remove `<v:roundrect>`, `<w:anchorlock>` etc. |
| Remove white backgrounds | Prevent white-on-white (invisible content in dark theme) |
| Force white text | Fix button text color on colored backgrounds |

## Related Helpers

```typescript
// Quoted-printable decoder
function decodeQuotedPrintable(input: string): string {
  return input
    .replace(/=\r\n/g, '')
    .replace(/=\n/g, '')
    .replace(/=([0-9A-Fa-f]{2})/g, (_, hex) => String.fromCharCode(parseInt(hex, 16)));
}

// Auto-link URLs in text
function linkifyText(text: string): string {
  return text.replace(/(https?:\/\/[^\s<>"']+)/g,
    '<a href="$1" target="_blank" rel="noopener noreferrer" style="color:#60a5fa;text-decoration:underline;word-break:break-all;">$1</a>');
}
```

## CSS Overrides (emailStyles)

```css
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
```

## Common Pitfalls

1. **`<!--[if !mso]>` is an HTML comment** — modern browsers don't render content inside it. MUST strip the delimiters but keep content.
2. **`background-color: #FFF`** (short hex) must be caught alongside `#ffffff`.
3. **`height: 17px`** on buttons makes them invisible. Override to `auto`.
4. **`mso-hide: all`** hides buttons from ALL browsers, not just Outlook.
5. **`-->` artifacts** from partial comment stripping can appear as visible text.
6. **`<!--[if` in CSS emailStyles is INVALID CSS** — breaks entire `<style>` tag → all email content renders as blank. NEVER include HTML comment syntax in CSS selectors. Use `.email-html-content xml` not `.email-html-content <!--[if`.
7. **emailStyles must use `.email-html-content noscript, .email-html-content xml`** — the broken version had `.email-html-content <!--[if` which is not valid CSS.
8. **Dark theme white-on-white** — `#FFF`, `#F2F4F6`, `#FAF9F5` backgrounds make content invisible on dark containers. Strip ALL light colors.
9. **Error boundary** — wrap `dangerouslySetInnerHTML` in try-catch, fallback to raw text on crash.
