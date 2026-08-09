#!/usr/bin/env python3
"""NoHalu challenge runner helper. Usage: python3 nohalu_run.py <challenge_id> [api_base]"""

import json
import sys
import subprocess

def curl(method, url, token=None, data=None):
    """Execute a curl command and return parsed JSON."""
    cmd = ["curl", "-s", "-X", method, url, "-H", "Content-Type: application/json"]
    if token:
        cmd += ["-H", f"Authorization: Bearer {token}"]
    if data:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            f.flush()
            cmd += ["-d", f"@{f.name}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)

def create_run(challenge_id, api_base):
    """Create a new run and return run_id + token."""
    resp = curl("POST", f"{api_base}/runs", data={"challenge_id": challenge_id, "agent_type": "generic"})
    return resp["run_id"], resp["agent_token"]

def activate(run_id, token, api_base):
    """Activate run by fetching challenge. Returns challenge, context, items."""
    challenge = curl("GET", f"{api_base}/runs/{run_id}/challenge", token)
    context = curl("GET", f"{api_base}/runs/{run_id}/context", token)
    items = curl("GET", f"{api_base}/runs/{run_id}/items", token)
    return challenge, context, items

def inspect_item(run_id, token, item_id, api_base):
    """Inspect a single item (handles 503 flaky retry)."""
    resp = curl("GET", f"{api_base}/runs/{run_id}/items/{item_id}", token)
    if isinstance(resp, dict) and resp.get("detail", {}).get("error_code") == "temporary_error":
        print(f"  [RETRY] {item_id} returned 503, retrying...")
        resp = curl("GET", f"{api_base}/runs/{run_id}/items/{item_id}", token)
    return resp

def take_action(run_id, token, action_data, api_base):
    """Take an action on a run."""
    return curl("POST", f"{api_base}/runs/{run_id}/actions", token, action_data)

def complete(run_id, token, summary, claims, api_base):
    """Complete the run with summary and claims."""
    return curl("POST", f"{api_base}/runs/{run_id}/complete", token, {"summary": summary, "claims": claims})

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <challenge_id> [api_base]")
        sys.exit(1)
    challenge_id = sys.argv[1]
    api_base = sys.argv[2] if len(sys.argv) > 2 else "https://api.nohalu.xyz/api/v1"
    
    run_id, token = create_run(challenge_id, api_base)
    print(f"Run created: {run_id}")
    print(f"Token: {token}")
    print(f"Next: curl -s -H 'Authorization: Bearer {token}' {api_base}/runs/{run_id}/challenge")
