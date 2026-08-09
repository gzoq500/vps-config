# Xiaomi MiMo Platform Signup — Real-World Example

## URL Structure

Base: `https://global.account.xiaomi.com/fe/service/register/email`

Critical params (contain auth tokens — must be preserved exactly):
- `_sign` — session signature
- `serviceParam` — JSON-encoded service config
- `sid` — service ID (`api-platform`)
- `callback` — post-auth redirect URL
- `followup` — final destination after callback
- `qs` — nested callback params (double URL-encoded)
- `_locale` / `region` / `_uRegion` — locale settings

## Form Fields Detected

| Field | Selector | Type |
|-------|----------|------|
| Country | `button "Indonesia"` | Custom dropdown (combobox) |
| Email | `textbox "Email"` | Text input |
| Password | `textbox "Enter your new password"` | Password input |
| Confirm Password | `textbox "Confirm new password"` | Password input |
| Agreement | `checkbox "I've read and agreed..."` | Checkbox |
| Submit | `button "Next"` (disabled until filled) | Button |

## Password Requirements

8-16 characters, combining at least 2 of:
- Digits (0-9)
- Letters (a-zA-Z)
- Special symbols

## Post-Submit Behavior

- Error elements: check `.error`, `.err-tip`, `[class*="error"]`
- May redirect to email verification or CAPTCHA page
- Final success redirects to `platform.xiaomimimo.com/console/balance`

## Gotchas

- Country selector is a custom component, not native `<select>`. Default is Indonesia.
- "Next" button is `disabled` until all fields are filled AND checkbox is checked.
- The `_sign` and `callback` params are session-bound — reusing them later may fail.
- **Xiaomi uses reCAPTCHA Enterprise** (verified 2026-07-17). Sitekey: `6LeBM0ocAAAAAEwYcFUjtxpVbs-0rnbSVXBBXmh4`. Loaded via `https://www.google.com/recaptcha/enterprise.js`. The captcha appears as an iframe AFTER the form is submitted (not on page load). Third-party solvers that DON'T support reCAPTCHA Enterprise (like Solverify) cannot solve it. Need 2captcha, CapSolver, or Anti-Captcha which support reCAPTCHA Enterprise task types.
