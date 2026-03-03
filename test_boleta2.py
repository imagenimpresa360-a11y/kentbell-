
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

async def click_boleta2():
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
            
            await page.wait_for_selector('a:has-text("SELECCIONAR")', timeout=30000)
            async with page.expect_navigation():
                await page.locator('a:has-text("SELECCIONAR")').click()
            
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            
            print("Looking for Boleta Exenta with aria-label...")
            el = page.locator('aria-label="Boleta Exenta"')
            # In playwright, aria-label selectors can be done via get_by_label
            print(f"By label count: {await page.get_by_label('Boleta Exenta').count()}")
            
            if await page.get_by_label('Boleta Exenta').count() > 0:
                await page.get_by_label('Boleta Exenta').first.click()
            else:
                # Let's try to click the sidebar specifically using x path or CSS
                await page.locator('.sidebar, md-sidenav').get_by_text('Boleta Exenta', exact=True).first.click()
            
            await asyncio.sleep(5)
            print("URL:", page.url)
            await page.screenshot(path="lioren_boletas2.png")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(click_boleta2())
