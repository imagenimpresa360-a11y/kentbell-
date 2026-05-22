
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

async def explore_lioren_robustly():
    load_dotenv()
    USER = os.getenv('LIOREN_USER')
    PASS = os.getenv('LIOREN_PASS')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            print("Login...")
            await page.goto("https://www.lioren.cl/login")
            await page.locator('input[name="email"]').fill(USER)
            await page.locator('input[name="password"]').fill(PASS)
            await page.get_by_role("button", name="INICIAR SESIÓN").click()
            
            await asyncio.sleep(8)
            await page.screenshot(path="lioren_after_login.png")
            
            # Check for selection button
            sel_btn = page.get_by_text("SELECCIONAR")
            if await sel_btn.count() > 0:
                print("Clicking SELECCIONAR...")
                await sel_btn.first.click()
                await asyncio.sleep(5)
                await page.screenshot(path="lioren_after_select.png")
            
            # Try to find Ventas link
            ventas = page.get_by_text("Ventas", exact=False)
            if await ventas.count() > 0:
                print("Clicking Ventas...")
                await ventas.first.click()
                await asyncio.sleep(2)
                await page.screenshot(path="lioren_ventas_expanded.png")
            
            # Print all visible links
            links = await page.locator('a').all()
            for link in links:
                t = await link.inner_text()
                h = await link.get_attribute('href')
                print(f"L: {t.strip()} -> {h}")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(explore_lioren_robustly())
