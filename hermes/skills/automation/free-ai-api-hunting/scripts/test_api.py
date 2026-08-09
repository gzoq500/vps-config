#!/usr/bin/env python3
"""Quick API provider test — list models + basic chat test.

Usage: python3 test_api.py <base_url> <api_key> [model]

Examples:
  python3 test_api.py https://api.gnrt.dev/v1 sk-gnrt-xxx
  python3 test_api.py https://api.b.ai/v1 sk-e7p-xxx qwen3.6-27b
"""

import json
import subprocess
import sys

def call(url, key, model, prompt, max_tokens=200):
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    })
    r = subprocess.run(
        ["curl", "-s", "--max-time", "25", url + "/chat/completions",
         "-H", f"Authorization: Bearer {key}",
         "-H", "Content-Type: application/json",
         "-d", payload],
        capture_output=True, text=True
    )
    try:
        return json.loads(r.stdout)
    except:
        return {"raw": r.stdout[:500]}

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    base = sys.argv[1].rstrip("/")
    key = sys.argv[2]
    model = sys.argv[3] if len(sys.argv) > 3 else None

    # 1. List models
    print(f"=== Models @ {base} ===")
    r = subprocess.run(
        ["curl", "-s", "--max-time", "10", base + "/models",
         "-H", f"Authorization: Bearer {key}"],
        capture_output=True, text=True
    )
    try:
        d = json.loads(r.stdout)
        models = sorted([m["id"] for m in d.get("data", [])])
        print(f"Total: {len(models)} models")
        for m in models:
            print(f"  {m}")
    except:
        print(f"Error: {r.stdout[:300]}")
        return

    # 2. Test specific model or first one
    if not model:
        model = models[0] if models else None
    if not model:
        print("No models to test")
        return

    print(f"\n=== Chat Test: {model} ===")
    result = call(base, key, model, "What exact model are you? 1 sentence.", 200)

    if "error" in result:
        print(f"❌ Error: {json.dumps(result['error'], indent=2)[:300]}")
    elif "choices" in result:
        choice = result["choices"][0]
        content = choice.get("message", {}).get("content", "")
        reasoning = choice.get("message", {}).get("reasoning_content", "")
        usage = result.get("usage", {})
        rtok = usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
        resp_model = result.get("model", "?")

        print(f"✅ Response model: {resp_model}")
        print(f"   Reasoning tokens: {rtok}")
        if reasoning:
            print(f"   Reasoning: {reasoning[:200]}")
        print(f"   Content: {content[:300]}")
    else:
        print(f"❓ Unknown: {json.dumps(result, indent=2)[:300]}")

if __name__ == "__main__":
    main()
