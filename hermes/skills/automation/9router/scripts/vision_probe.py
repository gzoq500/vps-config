#!/usr/bin/env python3
"""Probe which models on a 9Router (or any OpenAI-compatible) endpoint can
actually SEE an image.

Why this exists: a single solid-colour probe is guessable — a model that
silently drops the image and answers "red" scores a false pass. This builds a
TWO-COLOUR split image and demands the format `left=COLOR, right=COLOR`, so a
blind guess is very unlikely to match. Change LEFT/RIGHT between runs.

Run from execute_code (preferred — no approval gate on raw-IP hosts) or as a
plain script:

    python3 scripts/vision_probe.py

Edit BASE / KEY / CANDIDATES below, or import probe() and call it.
"""

import base64
import json
import struct
import urllib.error
import urllib.request
import zlib

# ---------------------------------------------------------------- config
BASE = "http://127.0.0.1:8443/v1/chat/completions"
KEY = "REPLACE_WITH_9ROUTER_PROXY_KEY"

# Vary these between runs so a memorised answer can't pass.
LEFT = (25, 90, 230)    # blue
RIGHT = (250, 215, 20)  # yellow
LEFT_NAME, RIGHT_NAME = "blue", "yellow"

CANDIDATES = [
    "xkiro/qwen/qwen3-vl-plus",
    "xkiro/qwen/qwen3.5-omni-plus",
    "xkiro/qwen/qwen3-omni-flash",
    "xkiro/nvidia/nemotron-3-nano-omni",
]

PROMPT = (
    "This image is split into two halves. What color is the LEFT half and "
    "what color is the RIGHT half? Answer only in the format: "
    "left=COLOR, right=COLOR"
)
MAX_TOKENS = 60  # keep >=40: reasoning models eat the budget and return empty


# ------------------------------------------------------------- image gen
def split_png(w: int, h: int, left_rgb, right_rgb) -> bytes:
    """Minimal stdlib PNG: left half left_rgb, right half right_rgb."""
    raw = b""
    for _ in range(h):
        row = b""
        for x in range(w):
            row += bytes(left_rgb if x < w // 2 else right_rgb)
        raw += b"\x00" + row

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return (
            struct.pack(">I", len(data))
            + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


# ----------------------------------------------------------------- probe
def ask(model: str, data_url: str, base: str = BASE, key: str = KEY):
    """Return (status, text). status in {OK, EMPTY, ERR}."""
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "max_tokens": MAX_TOKENS,
        "stream": False,
    }
    req = urllib.request.Request(
        base,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
    )
    try:
        raw = urllib.request.urlopen(req, timeout=90).read().decode()
        # 9Router sometimes emits concatenated JSON frames — raw_decode
        # takes the first complete object and ignores trailing bytes.
        obj, _ = json.JSONDecoder().raw_decode(raw)
        msg = obj["choices"][0]["message"]
        content = (msg.get("content") or "").strip()
        if not content:
            return "EMPTY", "[reasoning-only] " + (msg.get("reasoning_content", "")[:80])
        return "OK", content[:150]
    except urllib.error.HTTPError as e:
        return "ERR", f"HTTP {e.code}: {e.read().decode()[:160]}"
    except Exception as e:  # noqa: BLE001 - report anything, keep looping
        return "ERR", f"{type(e).__name__}: {e}"


def probe(models=None, base: str = BASE, key: str = KEY) -> dict:
    models = models or CANDIDATES
    data_url = "data:image/png;base64," + base64.b64encode(
        split_png(128, 64, LEFT, RIGHT)
    ).decode()

    results = {}
    for m in models:
        status, text = ask(m, data_url, base, key)
        lowered = text.lower()
        correct = LEFT_NAME in lowered and RIGHT_NAME in lowered
        icon = "✅" if (status == "OK" and correct) else ("⚠️" if status != "ERR" else "❌")
        print(f"{icon} {m}\n   -> {text}\n")
        results[m] = {"status": status, "correct": correct, "text": text}
    return results


if __name__ == "__main__":
    print(f"Expecting: left={LEFT_NAME}, right={RIGHT_NAME}\n")
    probe()
