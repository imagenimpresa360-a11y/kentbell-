
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

        print("1. Navigating to https://boxmagic.cl/login")
        try:
            await page.goto("https://boxmagic.cl/login", wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"   Goto error: {e}")

        # Check for "Panel de administración" (Welcome screen)
        # It's likely a button or link
        welcome_screen = await page.get_by_text("Panel de administración").count() > 0
        if welcome_screen:
            print("2. Welcome screen detected! Clicking 'Panel de administración'...")
            await page.get_by_text("Panel de administración").click()
        else:
            print("2. Standard login form detected (or unknown state). Filling credentials...")
            try:
                # Revised selectors based on dump
                email_sel = "input[data-bmid='input-email-ingreso']"
                pass_sel = "input[data-bmid='input-password-ingreso']"
                
                await page.wait_for_selector(email_sel, timeout=10000)
                await page.fill(email_sel, USER)
                await page.keyboard.press("Tab") 
                
                await page.fill(pass_sel, PASS)
                await page.keyboard.press("Tab") 
                
                print("3. Clicking login button...")
                btn_sel = "[data-bmid='btn-ingresar']"
                await page.click(btn_sel)
                
            except Exception as e:
                print(f"   Input filling/click error: {e}")
                await page.screenshot(path=os.path.join(DEBUG_DIR, "login_error_v4.png"))
                return

        print("4. Waiting for dashboard...")
        try:
            # Wait for URL change or a specific dashboard element
            await page.wait_for_url("**/dashboard**", timeout=30000)
            print("   SUCCESS! Dashboard loaded.")
            print(f"   URL: {page.url}")
            
            # Save dashboard HTML for next step analysis
            content = await page.content()
            with open("dashboard_logged_in.html", "w", encoding="utf-8") as f:
                f.write(content)
            print("   Saved dashboard_logged_in.html")
            
            await page.screenshot(path=os.path.join(DEBUG_DIR, "dashboard_success_v4.png"))
            
        except Exception as e:
            print("   Login failed or timed out.")
            print(f"   URL: {page.url}")
            await page.screenshot(path=os.path.join(DEBUG_DIR, "login_failed_v4.png"))

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
