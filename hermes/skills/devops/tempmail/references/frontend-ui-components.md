# TempMail Frontend UI Components

## Email Card (Active Alias)

Dark theme card with email address header + 2×2 button grid:

```
┌─────────────────────────┐
│ user@routerssh.web.id 📋│  ← header with copy icon
├──────────┬──────────────┤
│  Change  │    Copy      │
├──────────┼──────────────┤
│  Delete  │   Refresh    │
└──────────┴──────────────┘
```

### Styling classes:
- Card: `card overflow-hidden`
- Header: `bg-gray-800/80 border-b border-gray-700/50`
- Email text: `text-sm font-mono text-purple-300`
- Grid: `grid grid-cols-2 gap-px bg-gray-700/50 m-4 rounded-xl overflow-hidden`
- Buttons: `bg-gray-800/80 hover:bg-gray-700 text-gray-200 text-sm font-medium`

## Change Email Modal

Modal with input username + domain display + Random + Apply buttons.

- Title: "Change Your Address"
- Username input: placeholder "username (or leave empty)"
- Domain: displayed as `@routerssh.web.id` (read-only)
- Random button: calls `/api/alias` with empty body → generates random
- Apply button: calls `/api/alias` with `{email: "username@domain"}`
- Close: X button top-right

### Backend support:
- `POST /api/alias` → random email
- `POST /api/alias {"email": "custom@domain"}` → custom email

## Email Detail Rendering

### extractHtmlFromMime()
Strips from raw MIME content:
- `<head>...</head>` (CSS, meta)
- `<!--[if mso]>...<![endif]-->` (MSO conditionals)
- `<style>...</style>` blocks
- `<!--[...]-->` HTML comments
- `<img width="1" height="1">` tracking pixels

### Email HTML CSS
```css
.email-html-content { max-width: 100%; overflow-x: auto; }
.email-html-content * { max-width: 100% !important; box-sizing: border-box; }
.email-html-content img { max-width: 100% !important; border-radius: 8px; }
.email-html-content a { color: #2563eb !important; text-decoration: underline; }
.email-html-content table { max-width: 100% !important; }
.email-html-content td { max-width: 100% !important; word-wrap: break-word; }
.email-html-content img[width="1"][height="1"] { display: none !important; }
```

### Fallback: Text body with linkify
If no HTML, decode QP and linkify URLs:
```tsx
{email.body_text.split(/(https?:\/\/[^\s<>"']+)/g).map((part, i) => 
  part.match(/^https?:\/\//) ? (
    <a key={i} href={part} target="_blank">{part}</a>
  ) : <span key={i}>{part}</span>
)}
```
