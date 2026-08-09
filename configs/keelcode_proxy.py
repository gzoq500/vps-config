#!/usr/bin/env python3
import json, http.server, urllib.request, urllib.error, sys, os, time

KEELCODE_URL = "https://api.keelcode.ai/v1/messages"
TOKENS_FILE = "/root/.keelcode_tokens.json"
MODEL_MAP = {
    "gpt-4o-mini": "deepseek-v4-flash", "gpt-4o": "deepseek-v4-flash",
    "gpt-4": "deepseek-v4-flash", "gpt-3.5-turbo": "deepseek-v4-flash",
    "claude-3-haiku": "kimi-k2.6", "claude-3-sonnet": "kimi-k3",
    "claude-3-opus": "deepseek-v4-pro",
}
token_idx = 0
def load_tokens():
    return json.load(open(TOKENS_FILE))
def get_token():
    global token_idx
    tokens = load_tokens()
    if not tokens: return None
    t = tokens[token_idx % len(tokens)]
    token_idx += 1
    return t
def log(msg): print(f"[proxy] {msg}", file=sys.stderr, flush=True)
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        if "/chat/completions" not in self.path:
            self.send_response(404); self.end_headers(); return
        ln = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(ln)) if ln else {}
        raw_model = body.get("model", "deepseek-v4-flash")
        model = MODEL_MAP.get(raw_model, raw_model)
        msg_parts, system_parts = [], []
        for m in body.get("messages", []):
            if m.get("role") == "system":
                system_parts.append(m.get("content", ""))
            else:
                c = m.get("content", "")
                if isinstance(c, str):
                    msg_parts.append({"role": m["role"], "content": [{"type": "text", "text": c, "cache_control": {"type": "ephemeral"}}]})
                else:
                    msg_parts.append(m)
        abody = {"model": model, "max_tokens": min(body.get("max_tokens", 1024), 4096), "stream": True,
                 "messages": msg_parts or [{"role": "user", "content": [{"type": "text", "text": "Hi", "cache_control": {"type": "ephemeral"}}]}]}
        if system_parts:
            abody["system"] = [{"type": "text", "text": "\n".join(system_parts), "cache_control": {"type": "ephemeral"}}]
        log(f"REQ model={model} ({raw_model}) tokens={abody['max_tokens']}")
        for attempt in range(4):
            token = get_token()
            if not token: self.send_response(500); self.end_headers(); self.wfile.write(b'{"error":"no tokens"}'); return
            req = urllib.request.Request(KEELCODE_URL, data=json.dumps(abody).encode(),
                headers={"Authorization": "Bearer " + token, "Content-Type": "application/json",
                         "anthropic-version": "2023-06-01", "User-Agent": "keelcode-cli/1.0.0"}, method="POST")
            try:
                resp = urllib.request.urlopen(req, timeout=120)
                raw = resp.read().decode()
                break
            except urllib.error.HTTPError as e:
                err = e.read().decode()
                if e.code == 429:
                    log(f"429 rate limit, rotating token (attempt {attempt+1})")
                    time.sleep(1)
                    continue
                log(f"ERR {e.code}: {err[:200]}")
                self.send_response(e.code); self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"error": {"message": err, "code": e.code}}).encode()); return
        text_parts, thinking_parts = [], []
        for line in raw.splitlines():
            if not line.startswith("data: "): continue
            try: ev = json.loads(line[6:])
            except: continue
            if ev.get("type") == "content_block_delta":
                d = ev.get("delta", {})
                if d.get("type") == "text_delta": text_parts.append(d.get("text", ""))
                elif d.get("type") == "thinking_delta": thinking_parts.append(d.get("thinking", ""))
        content = "".join(text_parts)
        thinking = "".join(thinking_parts)
        log(f"RES content={len(content)}c thinking={len(thinking)}c")
        result = {"id": "chatcmpl-keelcode", "object": "chat.completion", "model": raw_model,
                  "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
                  "usage": {"prompt_tokens": 0, "completion_tokens": len(content.split()), "total_tokens": len(content.split())}}
        if thinking: result["choices"][0]["message"]["reasoning_content"] = thinking
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(json.dumps(result).encode())
if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3456
    host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
    t = load_tokens()
    log(f"Keelcode proxy on :{port} ({len(t)} tokens)")
    http.server.HTTPServer((host, port), Handler).serve_forever()