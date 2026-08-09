#!/usr/bin/env python3
"""Keelcode Google OAuth E2E registration + token generator.
Usage: python3 keelcode_register.py --accounts accounts.txt --headless
Token saved to results.json → extract tokens[access_token]
"""
# See /root/keelcode_register.py for full source
# Key flow:
# 1. Login via Google OAuth in headless browser (cloakbrowser)
# 2. Device code grant → approve in browser
# 3. Poll for access_token
# 4. Test all models via Anthropic API
# 5. Save results to results.json
#
# Dependencies: pip install cloakbrowser && playwright install chromium
# accounts.txt format: email@gmail.com,password
