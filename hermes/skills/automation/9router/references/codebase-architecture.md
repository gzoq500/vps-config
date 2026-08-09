# 9Router Codebase Architecture (v0.5.40, github.com/decolua/9router)

Analyzed for a potential C++ rebuild (Crow/Oat++ + nlohmann/json). ~820 JS files
excluding tests/gitbook. Clone with `git clone --depth 1` to /tmp for inspection.

## Layout

- `open-sse/` — **core router engine** (~300+ files). The valuable part (~30% of value, 10% of code).
  - `handlers/chatCore.js` — main request pipeline: detect format → translate request →
    RTK compress → executor → stream/non-stream response → translate back → usage log.
  - `translator/` — format translation OpenAI ↔ Claude ↔ Gemini ↔ Kiro ↔ Cursor etc.
    `request/*.js` + `response/*.js` pairs, plus `concerns/` (thinking, toolCall, usage, images).
  - `executors/` — ~30 provider-specific executors (kiro, grok-cli, cursor, mimo-free,
    xiaomi-tokenplan, gemini-cli, codex...). Each handles auth quirks/custom transport.
  - `providers/registry/` — 100+ provider definitions (models, endpoints, pricing).
  - `rtk/` — token compression: filters for git diff/log/status, grep, ls, tree,
    smartTruncate; plus caveman/ponytail prompt compressors, headroom, pxpipe.
  - `services/` — tokenRefresh (OAuth per provider), accountFallback, usage tracking, combos.
- `src/app/api/` — Next.js API routes; `/api/v1/*` = OpenAI-compatible endpoints
  (chat/completions, messages, responses, embeddings, images, audio, videos).
- `src/lib/db/` — SQLite with 4 adapter backends (better-sqlite3, bun, node, sql.js) + repos.
- `src/mitm/` — MITM proxy w/ cert generation for Antigravity/Copilot/Cursor/Kiro interception.
- `cli/` — terminal UI + system tray. `gitbook/` — docs site. Dashboard = Next.js React (60%+ of codebase).

## C++ rebuild feasibility verdict

Feasible in C++ (Crow/Oat++ + nlohmann/json):
- HTTP proxy/router core, SSE streaming passthrough, JSON format translation,
  SQLite usage store, OAuth token refresh, config-driven provider registry.

Hard / not worth it in C++:
- Dashboard (Next.js React) — keep as separate SPA or drop.
- 100+ provider adapters (each has OAuth flow + quirks) — make config-driven, port ~10.
- RTK compression (regex-heavy text parsing), MITM TLS interception, Cursor protobuf, MCP bridge.

Estimate: core router+translator+registry(10 providers)+SQLite ≈ 6–9 weeks solo;
full parity 8–12+ weeks. Recommended alternatives: Rust (actix-web) or Go for
better HTTP/proxy ecosystem; or strip Node app to CLI-only.
