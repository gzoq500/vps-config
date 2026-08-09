# TokenRouter API — Provider Reference

**URL:** `https://api.tokenrouter.com/v1`
**Key format:** `sk-*`
**Models listed:** 120 (Aug 2026)
**OpenAI-compatible:** Yes

## Free Tier

Only **1 model works** without credits:
- `moonshotai/kimi-k3-free` → actual model: `kimi-k3` (Moonshot AI)

All other models (including `:free` suffixed ones) return:
```
"User's credit limit is insufficient, remaining credit limit: $0.000000"
```

## Kimi K3 Free — Verified Identity

- **Model:** `kimi-k3` (Moonshot AI / 月之暗面)
- **Has reasoning_content:** ✅ (chain-of-thought, ~113 reasoning tokens per response)
- **Self-identify:** "I'm Kimi, an AI assistant developed by Moonshot AI"
- **Architecture:** Reasoning model (reasoning_tokens present)
- **Rate limit:** VERY STRICT — 2-3 requests then empty responses for several minutes
- **Response format:** `content: null` when max_tokens too low (all tokens go to reasoning)
- **Minimum max_tokens:** 200+ for actual content output (reasoning consumes most tokens)

## Adding to 9Router

```
Prefix: tokenrouter
Base URL: https://api.tokenrouter.com/v1
API Key: <tokenrouter key>
Default Model: moonshotai/kimi-k3-free
```

## Pitfalls

1. **Rate limiting is severe** — free model allows 2-3 requests then goes silent. Not suitable for production use.
2. **reasoning_tokens consume the budget** — with `max_tokens:50`, all tokens go to reasoning_content and `content` is null. Set `max_tokens:200+` for actual content.
3. **Model list is misleading** — 120 models listed but only 1 works on $0 balance.
4. **Not recommended for 9Router** — too rate-limited for reliable routing. Useful for occasional testing only.
