# Antigravity Cloud Code API Reference

## ⚠️ CRITICAL: User-Agent

**ONLY `Trae/1.0.0 antigravity-cockpit-tools` works.** ALL other UAs return 403 VALIDATION_REQUIRED:
- ❌ `google-api-nodejs-client/9.15.1 gemini-cli/0.34.0` (old, broken)
- ❌ `antigravity/ide/2.1.1 darwin/arm64` (9Router's default — BROKEN)
- ❌ empty string, `9Router`, any generic UA
- ✅ **`Trae/1.0.0 antigravity-cockpit-tools`** (ONLY working UA)

This is the #1 root cause of Antigravity 403 errors. See `9router-patching-pitfalls` skill for how to patch9Router's compiled chunks.

## API Endpoints

| Endpoint | URL |
|---|---|
| loadCodeAssist | `https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist` |
| onboardUser | `https://cloudcode-pa.googleapis.com/v1internal:onboardUser` |
| generateContent | `https://daily-cloudcode-pa.googleapis.com/v1internal:generateContent` |
| streamGenerateContent | `https://daily-cloudcode-pa.googleapis.com/v1internal:streamGenerateContent?alt=sse` |
| fetchAvailableModels | `https://cloudcode-pa.googleapis.com/v1internal:fetchAvailableModels` |

Note: `daily-cloudcode-pa` for generation, `cloudcode-pa` for setup/onboarding.

## Auth

OAuth2 with PKCE. Scopes:
- `https://www.googleapis.com/auth/cloud-platform`
- `https://www.googleapis.com/auth/userinfo.email`
- `https://www.googleapis.com/auth/userinfo.profile`
- `https://www.googleapis.com/auth/cclog`
- `https://www.googleapis.com/auth/experimentsandconfigs`

Client ID: `1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com`
Client Secret: `YOUR_CLIENT_SECRET`

Refresh token endpoint: `https://oauth2.googleapis.com/token`

## Onboarding Flow (MUST do before first generate)

### Step 1: loadCodeAssist
```json
POST https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist
Authorization: Bearer {access_token}
User-Agent: Trae/1.0.0 antigravity-cockpit-tools
{
  "metadata": {"ideType": 9, "platform": 0, "pluginType": 2},
  "mode": 1
}
```
**CRITICAL**: `platform` MUST be integer `0` (PLATFORM_UNSPECIFIED). String `"linux"` returns 400.

Response includes `allowedTiers` with tier ID (e.g., `"standard-tier"`).

### Step 2: onboardUser
```json
POST https://cloudcode-pa.googleapis.com/v1internal:onboardUser
Authorization: Bearer {access_token}
User-Agent: Trae/1.0.0 antigravity-cockpit-tools
{
  "metadata": {"ideType": 9, "platform": 0, "pluginType": 2},
  "tierId": "standard-tier",
  "cloudaicompanionProject": "project-id"
}
```
`cloudaicompanionProject` must be a STRING, not object.

Response: `{"done": true, "response": {"cloudaicompanionProject": {"id": "project-id"}}}`

### Step 3: generateContent (streaming)
```json
POST https://daily-cloudcode-pa.googleapis.com/v1internal:streamGenerateContent?alt=sse
Authorization: Bearer {access_token}
User-Agent: Trae/1.0.0 antigravity-cockpit-tools
{
  "project": "project-id",
  "model": "gemini-2.5-flash",
  "userAgent": "antigravity",
  "requestType": "agent",
  "requestId": "uuid",
  "request": {
    "contents": [
      {"role": "user", "parts": [{"text": "prompt"}]}
    ],
    "generationConfig": {
      "maxOutputTokens": 100,
      "temperature": 1,
      "topP": 0.95,
      "topK": 40
    },
    "sessionId": "antigravity:conversation:uuid",
    "safetySettings": []
  }
}
```

## Wrapper Format

The API uses a WRAPPER object (not raw Gemini format):
- `project`: GCP project ID (from onboardUser)
- `model`: model name (e.g., "gemini-2.5-flash")
- `userAgent`: "antigravity"
- `requestType`: "agent" or "image_gen"
- `requestId`: UUID string
- `request`: contains `contents`, `generationConfig`, `sessionId`, `safetySettings`

## VALIDATION_REQUIRED Error

If generateContent returns 403 with `VALIDATION_REQUIRED`:
1. Extract `validation_url` from `details[].metadata.validation_url`
2. User MUST visit this URL in a real browser (Google blocks Browserbase/automation)
3. Page shows "Autentikasi berhasil" (Authentication successful)
4. After validation, refresh token and retry — works immediately

Example validation URL:
```
https://accounts.google.com/signin/continue?sarp=1&scc=1&continue=https://developers.google.com/gemini-code-assist/auth/auth_success_gemini&...
```

## Available Models (13 total)

| Model ID | Upstream Model | Type |
|---|---|---|
| gemini-3.6-flash-high | gemini-3.6-flash-tiered(high) | Flash |
| gemini-3.6-flash-medium | gemini-3.6-flash-tiered(medium) | Flash |
| gemini-3.6-flash-low | gemini-3.6-flash-tiered(low) | Flash |
| gemini-3.5-flash-high | direct (404 — broken in9Router) | Flash |
| gemini-3.5-flash-medium | direct | Flash |
| gemini-3.5-flash-low | direct | Flash |
| gemini-3.5-flash-extra-low | direct | Flash |
| gemini-3.1-pro-high | direct | Pro |
| gemini-3.1-pro-low | direct | Pro |
| gemini-pro-agent | direct | Pro |
| claude-sonnet-4-6 | direct | Claude |
| claude-opus-4-6-thinking | direct | Claude |
| gpt-oss-120b-medium | direct | GPT |
| gemini-3-flash | direct | Flash |

Note: `gemini-3.5-flash-high` returns 404. Use `gemini-3-flash-agent` instead (mapped from same model).

## 9Router Integration

9Router prefix: `ag/` (e.g., `ag/gemini-3.6-flash-high`)
MITM domain: `daily-cloudcode-pa.googleapis.com`
OAuth callback: `http://localhost:20128/callback` (requires SSH tunnel from remote)

## Model Synonyms (9Router internal)
```
gemini-default → gemini-3.5-flash-low
gemini-3.5-flash-high → gemini-3-flash-agent
gemini-3-pro-high → gemini-pro-agent
claude → claude-sonnet-4-6
gpt.*oss → gpt-oss-120b-medium
```

## Google Search Grounding

Default: NO search tool. Inject `{google_search:{}}` into tools array.

**9Router patch (chunk 8499.js):**
```
Pattern: ...g&&{tools:g}
Replace: ...{tools:[...(g||[]),{google_search:{}}]}
```

This adds `google_search` to EVERY antigravity request. The API accepts it and grounds responses with real-time search data. Verified: returns current news (August 2026 headlines).

**Direct API test:**
```json
{
  "project": "project-id",
  "model": "gemini-2.5-flash",
  "request": {
    "contents": [{"role": "user", "parts": [{"text": "Latest AI news today"}]}],
    "tools": [{"google_search": {}}],
    "generationConfig": {"maxOutputTokens": 2000}
  }
}
```

Both `{"google_search": {}}` and `{"googleSearch": {}}` work. `googleSearchRetrieval` does NOT work (returns empty).

## Extended Reasoning (thinkingConfig)

Add to request body:
```json
{
  "thinkingConfig": {
    "includeThoughts": true,
    "thinkingBudget": 16384
  }
}
```

This enables System-2 thinking. Response includes reasoning_content with chain-of-thought (970-2282 tokens for complex tasks). Works on all Gemini models. Claude models ignore it (they have their own thinking).

## Auto-Patch Script

`/root/patch_antigravity.sh` restores all patches after `npm i -g 9router@latest`:
- User-Agent: `Trae/1.0.0 antigravity-cockpit-tools` in all chunks
- Google Search: `{google_search:{}}` injection in chunk 8499

Run after every9router update: `bash /root/patch_antigravity.sh`
