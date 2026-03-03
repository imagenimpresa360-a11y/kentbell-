
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

async def get_boletas_exentas():
    load_dotenv()
    USER = os.getenv('LIOREN_USER')
    PASS = os.getenv('LIOREN_PASS')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            accept_downloads=True,
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
                await page.locator('a:has-text("SELECCIONAR")').first.click()
            
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            
            print("Clicking 'Boleta Exenta'...")
            await page.get_by_text("Boleta Exenta").first.click()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            await page.screenshot(path="lioren_boletas_exentas.png")
            
            # See if there's a Sucursales filter
            print("Looking for Sucursal filter...")
            sucursales_select = await page.locator("select, input").all()
            for s in sucursales_select:
                name = await s.get_attribute("name")
                # print some details to see if we have filter inputs
            
            # Let's take a look at the Sucursales tab too
            print("Clicking 'Sucursales'...")
            try:
                await page.get_by_text("Sucursales").first.click()
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(3)
                await page.screenshot(path="lioren_sucursales.png")
            except:
                pass
            
            print("Done")
                
        except Exception as e:
            print(f"Error: {e}")
            await page.screenshot(path="lioren_boletas_err.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(get_boletas_exentas())
