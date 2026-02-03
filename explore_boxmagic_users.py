
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

USER = os.getenv('BOXMAGIC_USER')
PASS = os.getenv('BOXMAGIC_PASS')
URL_LOGIN = "https://auth.boxmagic.cl/" # Based on .env, but might redirect
# Usually BoxMagic login is at boxmagic.cl/login or similar. 
# .env says https://auth.boxmagic.cl/ which might be the SSO.

OUTPUT_DIR = os.path.join(os.getcwd(), "downloads", "boxmagic_exploration")
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1366, 'height': 768})
        page = await context.new_page()

        print("1. Navigating to login...")
        await page.goto("https://boxmagic.cl/login") 
        # Trying generic login first.

        print("2. Filling credentials...")
        # Check if we are on a login page
        try:
            await page.fill('input[name="email"]', USER)
            await page.fill('input[name="password"]', PASS)
            await page.click('button[type="submit"]') # Or whatever the button is
            print("   Login submitted.")
        except Exception as e:
            print(f"   Login form not found or error: {e}")
            await page.screenshot(path=os.path.join(OUTPUT_DIR, '01_login_fail.png'))
            return

        print("3. Waiting for dashboard...")
        await page.wait_for_timeout(10000) # Wait for redirects
        await page.screenshot(path=os.path.join(OUTPUT_DIR, '02_dashboard_or_error.png'))

        print("4. Dumping page content to find keywords...")
        content = await page.content()
        with open(os.path.join(OUTPUT_DIR, 'dashboard.html'), 'w', encoding='utf-8') as f:
            f.write(content)

        # keywords to look for: "Campanario", "Usuarios", "Clientes", "Inactivos"
        if "Campanario" in content:
            print("   Found 'Campanario' on page.")
        else:
            print("   'Campanario' NOT found.")

        print("5. Attempting to find profile switcher or side menu...")
        # Look for typical profile dropdowns
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
