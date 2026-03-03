
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

async def explore_lioren():
    load_dotenv()
    USER = os.getenv('LIOREN_USER')
    PASS = os.getenv('LIOREN_PASS')
    
    async with async_playwright() as p:
        # Usamos chromium con headless=False para debugear si fuera necesario, 
        # pero aquí forzamos True para el bot.
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            print("Login to Lioren...")
            await page.goto("https://www.lioren.cl/login")
            await page.get_by_placeholder("Email").fill(USER)
            await page.get_by_placeholder("Contraseña").fill(PASS)
            # El botón de login suele ser un submit
            await page.locator("button[type='submit']").click()
            
            # Esperar a que entre al dashboard
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            await page.screenshot(path="lioren_dashboard.png")
            print("Dashboard captured.")
            
            # Navegar a Ventas -> Listado de Boletas o similar
            # Busquemos 'Ventas' en el menú
            print("Finding 'Ventas' menu...")
            await page.get_by_text("Ventas").click()
            await asyncio.sleep(2)
            
            # Submenú 'Boletas' o 'Listado'
            # Intentemos buscar un link que contenga boletas o ventas
            print("Looking for Boletas/Documentos...")
            await page.screenshot(path="lioren_ventas_menu.png")
            
            # Intentar ir directo a la URL si la conocemos o intuimos
            # Basado en process_lioren, el reporte es 'Boletas Exentas'
            # Vamos a buscar links en la página
            links = await page.locator('a').all()
            for link in links:
                text = await link.inner_text()
                href = await link.get_attribute('href')
                if text and ('Ventas' in text or 'Boletas' in text):
                    print(f"Potential Link: {text.strip()} -> {href}")

        except Exception as e:
            print(f"Failed: {e}")
            await page.screenshot(path="lioren_error.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(explore_lioren())
