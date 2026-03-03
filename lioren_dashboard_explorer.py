
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

async def explore_lioren_dashboard():
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
            
            # Seleccionar empresa (Campanario es la única que sale)
            print("Selecting company...")
            await page.get_by_role("button", name="SELECCIONAR").click()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            await page.screenshot(path="lioren_real_dashboard.png")
            
            # Buscar menú Ventas
            print("Navigating to Ventas...")
            # En Lioren suele haber un sidebar.
            await page.locator('text="Ventas"').first.click()
            await asyncio.sleep(2)
            await page.screenshot(path="lioren_ventas_opciones.png")
            
            # Ver si hay algo como 'Reportes' o 'Exportar'
            # Vamos a 'Boletas' si existe
            # O mejor, vamos a 'Reportes' -> 'Ventas'
            try:
                await page.locator('text="Reportes"').click()
                await asyncio.sleep(2)
                await page.screenshot(path="lioren_reportes.png")
            except:
                print("No 'Reportes' menu found, continuing...")

        except Exception as e:
            print(f"Failed: {e}")
            await page.screenshot(path="lioren_dashboard_err.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(explore_lioren_dashboard())
