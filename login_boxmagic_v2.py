
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()
USER = os.getenv('BOXMAGIC_USER')
PASS = os.getenv('BOXMAGIC_PASS')

DEBUG_DIR = os.path.join(os.getcwd(), "downloads", "boxmagic_debug")
os.makedirs(DEBUG_DIR, exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 720})
        page = await context.new_page()

        print("1. Go to boxmagic.cl/login")
        try:
            await page.goto("https://boxmagic.cl/login", wait_until="networkidle", timeout=60000)
            # await page.goto("https://auth.boxmagic.cl/login/", wait_until="networkidle", timeout=60000) # Direct URL
        except Exception as e:
            print(f"   Goto error: {e}")

        print("2. dumping page title and url")
        print(f"   Title: {await page.title()}")
        print(f"   URL: {page.url}")

        print("3. Attempting to fill credentials...")
        
        # Try finding inputs by type first (worked before)
        await page.locator("input[type='email']").nth(0).fill(USER)
        await page.locator("input[type='password']").nth(0).fill(PASS)
        print("   Filled credentials.")

        print("4. Submitting...")
        
        # Strategy 1: button[type='submit']
        submit_btn = page.locator("button[type='submit']")
        if await submit_btn.count() > 0:
            print("   Found button[type='submit'], clicking...")
            await submit_btn.click()
        else:
            # Strategy 2: Look for 'Ingresar' text in any button
            print("   No type='submit', looking for text 'Ingresar'...")
            await page.locator("button", has_text="Ingresar").click()
            # If this fails, it will throw error, captured by try/except usually, but here checking count is safer.
            # But let's assume one of these works or we fall back.

        print("5. Waiting for navigation/dashboard...")
        try:
            # Wait for URL to change or a specific element of the dashboard
            await page.wait_for_url("**/dashboard**", timeout=20000) 
            print("   Navigation successful!")
            print(f"   New URL: {page.url}")
            
            # Take screenshot of dashboard
            await page.screenshot(path=os.path.join(DEBUG_DIR, "dashboard_success.png"))

            # NOW: We need to go to "Campanario" and "Informes" -> "Alumnos" -> "Inactivos"
            # But let's first confirm we are logged in.
            
        except Exception as e:
            print(f"   Navigation wait error: {e}")
            print("   Trying generic wait...")
            await asyncio.sleep(5)
            print(f"   Current URL: {page.url}")
            await page.screenshot(path=os.path.join(DEBUG_DIR, "login_attempt_result.png"))

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
