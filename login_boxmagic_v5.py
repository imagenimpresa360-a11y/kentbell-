
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
        # Try persistent context if possible? No, stick to new_context
        context = await browser.new_context(viewport={'width': 1280, 'height': 720})
        page = await context.new_page()

        print("1. Navigating to https://boxmagic.cl/login")
        await page.goto("https://boxmagic.cl/login", wait_until="networkidle", timeout=60000)

        # Dump HTML for analysis
        html_content = await page.content()
        with open("debug_login_page.html", "w", encoding="utf-8") as f:
            f.write(html_content)

        # Check for welcome screen text in HTML
        if "Panel de administración" in html_content:
            print("2. 'Panel de administración' found in HTML!")
            # Try to click it using various selectors
            try:
                print("   Clicking 'text=Panel de administración'...")
                await page.click("text=Panel de administración")
            except:
                print("   Click failed, trying partial text...")
                await page.click("text=Panel")
        else:
            print("2. Welcome screen NOT found. Proceeding with credentials...")
            try:
                # Revised selectors
                email_sel = "input[data-bmid='input-email-ingreso']"
                pass_sel = "input[data-bmid='input-password-ingreso']"
                btn_sel = "[data-bmid='btn-ingresar']"

                await page.wait_for_selector(email_sel, timeout=10000)
                await page.fill(email_sel, USER)
                await page.fill(pass_sel, PASS)
                await page.click(btn_sel)
            except Exception as e:
                print(f"   Credential entry error: {e}")
                
        print("3. Waiting for dashboard...")
        try:
            await page.wait_for_url("**/dashboard**", timeout=30000)
            print("   SUCCESS! Dashboard loaded.")
            print(f"   URL: {page.url}")
            
            content = await page.content()
            with open("dashboard_logged_in.html", "w", encoding="utf-8") as f:
                f.write(content)
            await page.screenshot(path=os.path.join(DEBUG_DIR, "dashboard_success_v5.png"))
            
        except:
            print("   Login failed or timed out.")
            print(f"   URL: {page.url}")
            await page.screenshot(path=os.path.join(DEBUG_DIR, "login_failed_v5.png"))

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
