
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

async def explore_lioren_internal():
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
            print("Login to Lioren...")
            await page.goto("https://www.lioren.cl/login")
            await page.locator('input[name="email"]').fill(USER)
            await page.locator('input[name="password"]').fill(PASS)
            await page.get_by_role("button", name="INICIAR SESIÓN").click()
            
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            await page.screenshot(path="lioren_internal_dashboard.png")
            print("Internal dashboard captured.")
            
            # Check for branch switcher
            print("Checking for branch switcher...")
            # Often it involves 'Sucursal' or 'Establecimiento'
            elements = await page.get_by_text("Marina", exact=False).all()
            print(f"Marina text found {len(elements)} times.")
            
            elements_camp = await page.get_by_text("Campanario", exact=False).all()
            print(f"Campanario text found {len(elements_camp)} times.")

            # Try to navigate to Ventas
            await page.get_by_text("Ventas").first.click()
            await asyncio.sleep(2)
            await page.screenshot(path="lioren_ventas_menu.png")
            
            # List links in Ventas menu
            links = await page.locator('.nav-link, a').all()
            for link in links:
                t = await link.inner_text()
                if t and ('Boletas' in t or 'Reportes' in t or 'Ventas' in t):
                    print(f"Menu Item: {t.strip()}")

        except Exception as e:
            print(f"Failed: {e}")
            await page.screenshot(path="lioren_internal_error.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(explore_lioren_internal())
