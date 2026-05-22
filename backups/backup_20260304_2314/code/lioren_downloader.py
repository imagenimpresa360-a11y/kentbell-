
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

async def download_lioren_report(branch_name, output_filename):
    load_dotenv()
    USER = os.getenv('LIOREN_USER')
    PASS = os.getenv('LIOREN_PASS')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Aceptar descargas
            accept_downloads=True,
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            print(f"Login for {branch_name}...")
            await page.goto("https://www.lioren.cl/login")
            await page.locator('input[name="email"]').fill(USER)
            await page.locator('input[name="password"]').fill(PASS)
            await page.get_by_role("button", name="INICIAR SESIÓN").click()
            
            await page.wait_for_selector('text="SELECCIONAR EMPRESA"', timeout=30000)
            
            # Seleccionar la empresa correcta
            await page.locator('span.select2-selection').click()
            await asyncio.sleep(1)
            # Buscar la opción que contenga el nombre de la sucursal
            # Si branch_name es 'Campanario', buscamos 'CAMPANARIO'
            branch_selector = f'li.select2-results__option:has-text("{branch_name.upper()}")'
            if await page.locator(branch_selector).count() > 0:
                await page.locator(branch_selector).first.click()
                print(f"Selected branch: {branch_name}")
            else:
                print(f"Branch {branch_name} not found in dropdown, proceeding with default.")
            
            await page.get_by_text("SELECCIONAR").click()
            await page.wait_for_load_state("networkidle")
            
            # Navegar a Ventas -> Listado o similar
            # Basado en la URL típica de Lioren para ventas
            print("Navigating to Ventas...")
            await page.goto("https://www.lioren.cl/ventas/emitidos", wait_until="networkidle")
            
            # Filtro de fechas
            print("Setting date filter for January 2026...")
            # Lioren suele usar inputs de fecha o un rango.
            # Intentemos buscar inputs de tipo date o con IDs comunes
            await page.locator('input[name="fecha_desde"]').fill("2026-01-01")
            await page.locator('input[name="fecha_hasta"]').fill("2026-01-31")
            
            # Clic en Filtrar / Buscar
            await page.get_by_role("button", name="Filtrar").click()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            
            # Botón Excel
            print("Downloading Excel...")
            async with page.expect_download(timeout=60000) as download_info:
                # El botón suele tener un icono de excel o decir 'Excel' o 'Exportar'
                await page.locator('button:has-text("Excel"), a:has-text("Excel"), .btn-excel').first.click()
            
            download = await download_info.value
            path = os.path.join("downloads", "lioren", "ventas", output_filename)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            await download.save_as(path)
            print(f"SUCCESS: Report saved to {path}")
            return True

        except Exception as e:
            print(f"Failed for {branch_name}: {e}")
            await page.screenshot(path=f"lioren_error_{branch_name}.png")
            return False
        finally:
            await browser.close()

async def main():
    # El usuario dijo 'Campanario' y 'Marina'
    await download_lioren_report("Campanario", "ventas_january_campanario.xlsx")
    await download_lioren_report("Marina", "ventas_january_marina.xlsx")

if __name__ == "__main__":
    asyncio.run(main())
