#!/usr/bin/env python3
"""
Xiaomi MiMo Platform - Auto Signup Script
Untuk keperluan testing/development.

Usage:
  python3 xiaomi_mimo_signup.py -e "email@kamu.com" -p "Password123!"
  python3 xiaomi_mimo_signup.py -e "email@kamu.com" -p "Password123!" --visible
"""

import asyncio
import sys
import getpass
from playwright.async_api import async_playwright

SIGNUP_URL = (
    "https://global.account.xiaomi.com/fe/service/register/email?"
    "_group=DEFAULT&_sign=iV9Q5kxBqXGdbkb6kmapXvJrkZM="
    '&serviceParam={"checkSafePhone":false,"checkSafeAddress":false,"lsrp_score":0.0}'
    "&showActiveX=false&theme=&needTheme=false&bizDeviceType="
    "&_locale=id_ID&source=&region=ID&sid=api-platform"
    "&qs=%3Fcallback%3Dhttps%253A%252F%252Fplatform.xiaomimimo.com%252Fsts%253Fsign%253DM7gfywevl3CG5YTTcZDifhK6IK8%25253D%2526followup%253Dhttps%25253A%25252F%25252Fplatform.xiaomimimo.com%25252Fconsole%25252Fbalance%26sid%3Dapi-platform"
    "&callback=https://platform.xiaomimimo.com/sts?sign=M7gfywevl3CG5YTTcZDifhK6IK8%3D"
    "&followup=https%3A%2F%2Fplatform.xiaomimimo.com%2Fconsole%2Fbalance"
    "&_uRegion=ID"
)


async def signup(email: str, password: str, headless: bool = False):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            locale="id-ID",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        print("[*] Opening signup page...")
        await page.goto(SIGNUP_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        # Fill email
        print(f"[*] Filling email: {email}")
        email_input = page.locator('input[type="text"], input[placeholder*="Email"]').first
        await email_input.click()
        await email_input.fill(email)

        # Fill password
        print("[*] Filling password...")
        pw_inputs = page.locator('input[type="password"]')
        await pw_inputs.nth(0).fill(password)
        await pw_inputs.nth(1).fill(password)  # confirm password

        # Check agreement checkbox
        print("[*] Checking agreement...")
        checkbox = page.locator('input[type="checkbox"]')
        await checkbox.check()
        await page.wait_for_timeout(500)

        # Click Next
        print("[*] Clicking Next...")
        next_btn = page.locator('button:has-text("Next")')
        await next_btn.click()
        await page.wait_for_timeout(3000)

        # Check for errors
        error_el = page.locator('.error, .err-tip, [class*="error"]')
        if await error_el.count() > 0:
            err_text = await error_el.first.text_content()
            if err_text and err_text.strip():
                print(f"[!] Error: {err_text.strip()}")
                await browser.close()
                return False

        # Check for verification (captcha / email code)
        page_text = await page.inner_text("body")
        if any(kw in page_text.lower() for kw in ["verify", "captcha", "code"]):
            print("[!] Verification required (CAPTCHA/email code).")
            if not headless:
                print("[*] Waiting for manual verification (120s timeout)...")
                try:
                    await page.wait_for_url("**/console/**", timeout=120000)
                    print("[✓] Signup successful! Redirected to console.")
                except Exception:
                    print("[!] Timeout. Check status manually.")
            else:
                print("[!] Re-run with --visible for manual verification.")
                await browser.close()
                return False
        else:
            print("[✓] Form submitted. Check page for result.")

        # Screenshot
        screenshot_path = "/root/xiaomi_mimo_signup_result.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"[*] Screenshot saved: {screenshot_path}")

        if not headless:
            print("[*] Browser open. Press Ctrl+C to exit.")
            await page.wait_for_timeout(30000)

        await browser.close()
        return True


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Xiaomi MiMo Signup Script")
    parser.add_argument("--email", "-e", help="Email for registration")
    parser.add_argument("--password", "-p", help="Password for registration")
    parser.add_argument("--visible", action="store_true", help="Show browser (non-headless)")
    args = parser.parse_args()

    email = args.email or input("Email: ").strip()
    password = args.password or getpass.getpass("Password (8-16 char, 2 of: digits/letters/symbols): ")

    if not email or not password:
        print("[!] Email and password are required.")
        sys.exit(1)

    if len(password) < 8 or len(password) > 16:
        print("[!] Password must be 8-16 characters.")
        sys.exit(1)

    await signup(email, password, headless=not args.visible)


if __name__ == "__main__":
    asyncio.run(main())
