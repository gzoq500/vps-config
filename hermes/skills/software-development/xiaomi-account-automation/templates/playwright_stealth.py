#!/usr/bin/env python3
"""
Playwright Stealth Launch Template
Anti-detection measures for bypassing bot fingerprinting (e.g., MiMo risk control).

Usage: Copy and modify for your specific flow.
Key: apply_stealth() must be called BEFORE any navigation.
"""
import asyncio
from playwright.async_api import async_playwright

# ── Stealth Configuration ──
STEALTH_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
STEALTH_VIEWPORT = {"width": 1366, "height": 768}
STEALTH_LOCALE = "en-US"
STEALTH_TIMEZONE = "America/New_York"  # Change to match proxy location

# ── Anti-detection JavaScript ──
STEALTH_JS = """
// Override navigator properties
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});

// Override permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);

// Override WebGL renderer
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter.apply(this, arguments);
};

// Override canvas fingerprint (add noise)
const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(type) {
    if (type === 'image/png') {
        const ctx = this.getContext('2d');
        if (ctx) {
            const style = ctx.fillStyle;
            ctx.fillStyle = 'rgba(0,0,0,0.01)';
            ctx.fillRect(0, 0, 1, 1);
            ctx.fillStyle = style;
        }
    }
    return originalToDataURL.apply(this, arguments);
};

// Chrome detection object
window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {}
};
"""

# ── Launch Args ──
STEALTH_ARGS = [
    '--no-sandbox',
    '--disable-blink-features=AutomationControlled',
    '--disable-features=IsolateOrigins,site-per-process',
    '--disable-site-isolation-trials',
    '--disable-infobars',
    '--window-size=1366,768',
]

# ── Extra HTTP Headers ──
STEALTH_HEADERS = {
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
}


async def create_stealth_browser(p):
    """Create a stealth Playwright browser with anti-detection."""
    browser = await p.chromium.launch(headless=False, args=STEALTH_ARGS)
    ctx = await browser.new_context(
        viewport=STEALTH_VIEWPORT,
        user_agent=STEALTH_UA,
        locale=STEALTH_LOCALE,
        timezone_id=STEALTH_TIMEZONE,
        color_scheme='light',
    )
    return browser, ctx


async def apply_stealth(page):
    """Apply stealth measures to a page. Call BEFORE navigating."""
    await page.add_init_script(STEALTH_JS)
    await page.set_extra_http_headers(STEALTH_HEADERS)


async def set_auth_cookies(ctx, service_token, pass_token, c_user_id, user_id):
    """Set MiMo authentication cookies."""
    await ctx.add_cookies([
        {"name": "api-platform_serviceToken", "value": service_token, "domain": "platform.xiaomimimo.com", "path": "/"},
        {"name": "passToken", "value": pass_token, "domain": ".account.xiaomi.com", "path": "/"},
        {"name": "cUserId", "value": c_user_id, "domain": ".account.xiaomi.com", "path": "/"},
        {"name": "userId", "value": user_id, "domain": ".account.xiaomi.com", "path": "/"},
    ])


# ── Example Usage ──
async def example():
    async with async_playwright() as p:
        browser, ctx = await create_stealth_browser(p)
        page = await ctx.new_page()
        await apply_stealth(page)
        
        # Set auth cookies (from API flow)
        # await set_auth_cookies(ctx, service_token, pass_token, c_user_id, user_id)
        
        await page.goto("https://example.com", timeout=30000)
        # ... your flow here ...
        await browser.close()

if __name__ == "__main__":
    asyncio.run(example())
