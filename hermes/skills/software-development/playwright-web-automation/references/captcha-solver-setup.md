# Captcha-Solver Sidecar — Setup Reference

## Repo

`https://github.com/waguriagentic/captcha-solver`

## Installation

```bash
cd /root
git clone https://github.com/waguriagentic/captcha-solver.git
cd captcha-solver
python3 -m venv .venv
# Install deps — use direct venv binary to avoid terminal-tool detection issues
.venv/bin/pip install fastapi uvicorn pydantic pillow onnxruntime opencv-python-headless numpy cloakbrowser
.venv/bin/python -m playwright install chromium
# System deps for headed mode
apt-get install -y xvfb
```

## Mistral API Keys (for image captcha solving)

File: `common/apikey.txt` — one key per line, round-robin with auto-failover.
Used by reCAPTCHA v2 image grid and hCaptcha image challenges.
Get keys at: https://console.mistral.ai/api-keys/

## Systemd Service

```bash
cat > /etc/systemd/system/captcha-solver.service << 'EOF'
[Unit]
Description=Captcha Solver HTTP Sidecar
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/captcha-solver
ExecStart=/usr/bin/xvfb-run /root/captcha-solver/.venv/bin/python server.py
Restart=on-failure
RestartSec=5
Environment=PORT=8877
Environment=TURNSTILE_HEADLESS=0
Environment=RECAPTCHA_HEADLESS=0
Environment=HCAPTCHA_HEADLESS=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable captcha-solver
systemctl start captcha-solver
```

## Health Check

```bash
curl -s http://127.0.0.1:8877/health
# Returns: {"status":"ok","supported_types":["turnstile","recaptcha","hcaptcha","cloudflare","awswaf","botguard","datadome","perimeterx","akamai","aliyun"]}
```

## API Usage

### Basic solve (route-intercept)
```bash
curl -X POST http://localhost:8877/solve \
  -H 'Content-Type: application/json' \
  -d '{"type":"turnstile","sitekey":"0x4AAAAAA...","url":"https://target.com"}'
```

### Real-page solve (navigate + interact)
```bash
curl -X POST http://localhost:8877/solve \
  -H 'Content-Type: application/json' \
  -d '{
    "type": "recaptcha", "version": "v2", "real_page": true,
    "url": "https://target.com/login",
    "pre_actions": [
      {"type": "fill", "selector": "input[type=email]", "value": "user@example.com"},
      {"type": "click", "selector": "button[type=submit]"}
    ],
    "post_fetch": [
      {"url": "https://target.com/api/verify", "body": {"token": "__TOKEN__"}}
    ]
  }'
```

### Cloudflare clearance
```bash
curl -X POST http://localhost:8877/solve \
  -H 'Content-Type: application/json' \
  -d '{"type":"cloudflare","url":"https://protected.example.com","proxy":"http://user:pass@ip:port"}'
```

## Response Format

All responses have uniform `"solved": true|false` at top level.

- Token types (turnstile/recaptcha/hcaptcha): returns `token`
- Page-level (cloudflare/awswaf): returns `cf_clearance` or `cookies`
- Error: `200` with `solved:false` + `error` (ran but failed) or `4xx/5xx` with `{detail}` (never solved)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8877` | HTTP server port |
| `TURNSTILE_HEADLESS` | `1` | `0` for headed (needs Xvfb) |
| `TURNSTILE_PROXY` | — | Residential proxy URL |
| `RECAPTCHA_HEADLESS` | `0` | Headed default for reCAPTCHA |
| `HCAPTCHA_HEADLESS` | `0` | Headed default for hCaptcha |

## Files Structure

```
captcha-solver/
├── server.py              # FastAPI server (unified /solve endpoint)
├── run.sh                 # Venv launcher
├── requirements.txt       # Deps manifest
├── common/
│   ├── browser.py         # Shared browser helpers (selectors, pre-actions, post_fetch)
│   ├── mistral.py         # Mistral vision KeyPool (round-robin, auto-failover)
│   └── apikey.txt         # Mistral API keys (one per line)
├── turnstile/             # Cloudflare Turnstile solver
├── recaptcha/             # reCAPTCHA v2/v3/Enterprise solver
├── hcaptcha/              # hCaptcha solver
├── cloudflare/            # Cloudflare clearance (cf_clearance cookie)
├── awswaf/                # AWS WAF token solver
├── botguard/              # Google BotGuard (OAuth token extraction)
├── datadome/              # DataDome clearance cookie
├── perimeterx/            # PerimeterX/HUMAN Press & Hold
├── akamai/                # Akamai Bot Manager _abck cookie
└── aliyun/                # Aliyun Captcha 2.0 slide-puzzle
```

## Pitfalls

- **Datacenter IPs**: Cloudflare/reCAPTCHA score datacenter IPs harshly. Residential proxy often required for hard targets.
- **cf_clearance binding**: Bound to IP + JA3/TLS + User-Agent. Must replay from same proxy with same UA.
- **Headed mode**: reCAPTCHA/hCaptcha default to headed (`HEADLESS=0`). Needs Xvfb on headless servers.
- **pip detection**: Terminal tool may flag `pip install` as long-lived process. Use `.venv/bin/pip` directly or wrap in a `.sh` script run via background process.
