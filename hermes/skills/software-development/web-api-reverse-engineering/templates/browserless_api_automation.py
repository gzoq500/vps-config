#!/usr/bin/env python3
"""
Template: Browserless Web API Automation Script

Adapt this template when reverse-engineering a web app's API to go browserless.
Fill in the CONSTANTS section with values extracted from the target site's JS.

Requirements: pip3 install pycryptodome requests
"""

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import time
import uuid
from urllib.parse import urlencode

import requests
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad

# =============================================================================
# CONSTANTS — Fill these in from JS bundle analysis
# =============================================================================

# AES encryption (from crypto chunk)
AES_KEY_CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
AES_IV = b"CHANGE_ME_16BYTE"  # UTF-8 bytes, NOT hex. Must be 16 bytes.

# RSA public key (from crypto chunk) — base64 SPKI format
RSA_KEY_B64 = "MIGfMA0GCSqGSIb3DQEBA..."

# API endpoints (from webpack module exports)
BASE_URL = "https://target.example.com"
ENDPOINTS = {
    "action1": "/api/action1",
    "action2": "/api/action2",
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


# =============================================================================
# CRYPTO — Replicate the site's JS crypto
# =============================================================================

def generate_random_key(length=16, charset=None):
    """Generate random key matching JS implementation."""
    import random
    charset = charset or AES_KEY_CHARSET
    return "".join(random.choice(charset) for _ in range(length))


def aes_cbc_encrypt(plaintext, key_bytes, iv_bytes):
    """AES-CBC PKCS7 encrypt → base64 string (matches CryptoJS .toString())."""
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
    padded = pad(plaintext.encode("utf-8"), AES.block_size)
    return base64.b64encode(cipher.encrypt(padded)).decode("ascii")


def rsa_encrypt_hex(plaintext_bytes, rsa_key):
    """RSA PKCS1v1.5 encrypt → hex string (matches JS RSAKey.encrypt())."""
    cipher = PKCS1_v1_5.new(rsa_key)
    return cipher.encrypt(plaintext_bytes).hex()


def encrypt_params(params, eui_key_b64=None):
    """Replicate the site's encryptAes() function. Adapt as needed."""
    eui_key_b64 = eui_key_b64 or RSA_KEY_B64
    random_key = generate_random_key(16)
    key_bytes = random_key.encode("utf-8")

    # RSA encrypt base64(key)
    rsa_key = RSA.import_key(base64.b64decode(eui_key_b64))
    enc_key = rsa_encrypt_hex(base64.b64encode(key_bytes), rsa_key)

    # AES encrypt each param
    encrypted = {}
    for k, v in params.items():
        encrypted[k] = aes_cbc_encrypt(str(v), key_bytes, AES_IV)

    # Build EUI
    field_names = base64.b64encode(",".join(params.keys()).encode()).decode()
    eui = f"{enc_key}.{field_names}"

    return {"EUI": eui, "encryptedParams": encrypted}


# =============================================================================
# API CLIENT
# =============================================================================

class WebAPIClient:
    def __init__(self, base_url=None):
        self.base_url = base_url or BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json, */*; q=0.01",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
        })

    def load_page(self, path="/"):
        """Load page to establish cookies."""
        resp = self.session.get(f"{self.base_url}{path}", timeout=15)
        print(f"[*] Loaded {path} — status {resp.status_code}, cookies: {len(self.session.cookies)}")
        return resp

    def post_form(self, endpoint, data, extra_headers=None):
        """POST form-urlencoded data, handle response wrapping."""
        headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
        if extra_headers:
            headers.update(extra_headers)

        url = f"{self.base_url}{endpoint}"
        print(f"[*] POST {url}")
        resp = self.session.post(url, data=urlencode(data), headers=headers, timeout=15)
        return self._parse_response(resp)

    def _parse_response(self, resp):
        """Parse response, stripping known JSON wrappers."""
        text = resp.text.strip()
        for prefix in ("&&&START&&&", "@json:"):
            if text.startswith(prefix):
                text = text[len(prefix):]
        # JSONP: callback({...})
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            text = m.group()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text, "status": resp.status_code}


# =============================================================================
# MAIN FLOW — Adapt to your target site
# =============================================================================

def run_signup(email, password, client=None):
    client = client or WebAPIClient()

    # Step 1: Load page for cookies
    client.load_page("/register")

    # Step 2: Encrypt params
    encrypted = encrypt_params({"user": email})
    print(f"[*] EUI: {encrypted['EUI'][:60]}...")

    # Step 3: First API call (e.g., send verification code)
    result1 = client.post_form(
        ENDPOINTS["action1"],
        {"sid": "passport", "user": encrypted["encryptedParams"]["user"]},
        extra_headers={"EUI": encrypted["EUI"]},
    )
    print(f"[*] Result: {json.dumps(result1, indent=2)[:300]}")

    # Step 4: Second API call (e.g., submit registration)
    result2 = client.post_form(
        ENDPOINTS["action2"],
        {
            "user": encrypted["encryptedParams"]["user"],
            "hash": hashlib.md5(password.encode()).hexdigest().upper(),
            "_json": "true",
        },
        extra_headers={"EUI": encrypted["EUI"]},
    )
    print(f"[*] Result: {json.dumps(result2, indent=2)[:300]}")

    return result2


def main():
    parser = argparse.ArgumentParser(description="Browserless Web API Automation")
    parser.add_argument("--email", "-e", required=True)
    parser.add_argument("--password", "-p", required=True)
    parser.add_argument("--test-crypto", action="store_true", help="Test crypto only")
    args = parser.parse_args()

    if args.test_crypto:
        result = encrypt_params({"user": args.email})
        print(f"EUI: {result['EUI']}")
        print(f"Encrypted: {result['encryptedParams']}")
        return

    run_signup(args.email, args.password)


if __name__ == "__main__":
    main()
