
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()
USER = os.getenv('BOXMAGIC_USER')
PASS = os.getenv('BOXMAGIC_PASS')

DEBUG_DIR = os.path.join(os.getcwd(), "downloads", "boxmagic_debug")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 720})
        page = await context.new_page()

        print("1. Go to boxmagic.cl/login")
        await page.goto("https://boxmagic.cl/login", wait_until="networkidle", timeout=60000)
        
        # Check if we see "Ruben"
        text = await page.inner_text("body")
        if "Ruben" in text:
            print("2. FOUND 'Ruben' on page. Attempting to click 'Panel'...")
            # Try multiple selectors for "Panel de administración"
            try:
                await page.get_by_text("Panel de administración").click()
                print("   Clicked 'Panel de administración' exact text.")
            except:
                try:
                    await page.click("text=Panel")
                    print("   Clicked 'text=Panel'.")
                except:
                    print("   Failed to click Panel. Dumping body...")
                    print(text[:500])
                    
        else:
            print("2. 'Ruben' NOT found. Filling form...")
            try:
                await page.fill("input[data-bmid='input-email-ingreso']", USER)
                await page.fill("input[data-bmid='input-password-ingreso']", PASS)
                await page.click("[data-bmid='btn-ingresar']")
            except Exception as e:
                print(f"   Form fill error: {e}")

        print("3. Waiting for dashboard...")
        try:
            await page.wait_for_url("**/dashboard", timeout=30000)
            print("   SUCCESS! Dashboard loaded.")
            # Save HTML
            with open("dashboard_final.html", "w", encoding="utf-8") as f:
                f.write(await page.content())
        except:
             print("   Login failed.")
             await page.screenshot(path=os.path.join(DEBUG_DIR, "login_final_fail.png"))

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
