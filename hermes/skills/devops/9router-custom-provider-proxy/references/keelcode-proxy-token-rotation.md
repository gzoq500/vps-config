# Keelcode Proxy — Token Rotation Reference

## Token Rotation Architecture

```
Client → 9Router → Proxy (port 3456) → keelcode.ai
                     ↓
              /root/.keelcode_tokens.json
              ["token1", "token2", "token3", "token4"]
                     ↓
              On 429 → rotate to next token
```

## Token Limits Per Model (per token per day)
- kimi-k3: 10 requests
- deepseek-v4-flash: ~50 requests
- deepseek-v4-pro: ~50 requests
- kimi-k2.6/k2.7-code: ~50 requests
- gpt-5.6-luna/sol/terra: ~50 requests

## Registration Script
```bash
# Single account
cd /root && python3 keelcode_register.py --accounts accounts.txt --headless

# Batch (from accounts.txt)
for i in $(seq 0 9); do
  python3 keelcode_register.py --accounts accounts.txt --account-index $i --headless
  # Extract token from results.json
done
```

## accounts.txt Format
```
email@domain.com,password
```

## Proxy Model Mapping
9Router validates "Default Model" against known models. The proxy maps unknown → known:
```python
MODEL_MAP = {
    "gpt-4o-mini": "deepseek-v4-flash",
    "gpt-4o": "deepseek-v4-flash",
    "claude-3-haiku": "kimi-k2.6",
    "claude-3-sonnet": "kimi-k3",
    "claude-3-opus": "deepseek-v4-pro",
}
```
Response returns ORIGINAL model name, not mapped.

## Systemd Service
```ini
[Unit]
Description=Keelcode Proxy (OpenAI to Anthropic translator)
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /root/keelcode_proxy.py 3456 0.0.0.0
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
