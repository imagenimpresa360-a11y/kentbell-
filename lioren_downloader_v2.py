
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
            
            # Esperar a que cargue la lista de empresas
            await asyncio.sleep(5)
            
            # Seleccionar empresa
            # Intentar ver si Marina está disponible en el dropdown si lo pedimos
            if branch_name == "Marina":
                print("Checking if Marina exists...")
                try:
                    await page.locator('span.select2-selection').click()
                    await asyncio.sleep(1)
                    branch_selector = f'li.select2-results__option:has-text("MARINA")'
                    if await page.locator(branch_selector).count() > 0:
                        await page.locator(branch_selector).first.click()
                        print("Selected MARINA.")
                    else:
                        print("MARINA NOT FOUND. Your account only has 1 company.")
                except:
                    print("Could not interact with dropdown.")
            
            # Clic en SELECCIONAR
            sel_btn = page.get_by_text("SELECCIONAR")
            if await sel_btn.count() > 0:
                await sel_btn.first.click()
            else:
                # Si no hay pantalla de selección, tal vez ya entró
                print("No selection screen, maybe already in dashboard.")
            
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)
            
            # Navegar a Ventas Emitidos
            print("Navigating to Ventas...")
            await page.goto("https://www.lioren.cl/ventas/emitidos", wait_until="networkidle")
            
            # Filtro de fechas
            print("Filtering January 2026...")
            try:
                # Buscar por ID si fallan los nombres
                await page.evaluate("""
                    () => {
                        document.querySelector('input[name="fecha_desde"]').value = '2026-01-01';
                        document.querySelector('input[name="fecha_hasta"]').value = '2026-01-31';
                    }
                """)
                # A veces hay que disparar el evento 'change'
                await page.get_by_role("button", name="FILTRAR").first.click()
            except:
                print("Fallback filtering...")
                if await page.locator('input[name="fecha_desde"]').count() > 0:
                    await page.locator('input[name="fecha_desde"]').fill("2026-01-01")
                    await page.locator('input[name="fecha_hasta"]').fill("2026-01-31")
                    await page.get_by_role("button", name="Filtrar").click()

            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            
            # Capturar lista de ventas para confirmar que hay datos
            await page.screenshot(path=f"lioren_ventas_{branch_name}.png")
            
            # Descargar Excel
            print("Attempting Excel download...")
            # El botón suele ser un dropdown 'Exportar' o directo 'Excel'
            excel_btn = page.get_by_text("Excel", exact=False).first
            if await excel_btn.count() > 0:
                async with page.expect_download(timeout=60000) as download_info:
                    await excel_btn.click()
                download = await download_info.value
                path = os.path.join("downloads", "lioren", "ventas", f"january_{branch_name.lower()}.xlsx")
                os.makedirs(os.path.dirname(path), exist_ok=True)
                await download.save_as(path)
                print(f"SUCCESS: {path}")
                return True
            else:
                print("EXCEL BUTTON NOT FOUND.")
                return False

        except Exception as e:
            print(f"Failed for {branch_name}: {e}")
            await page.screenshot(path=f"lioren_error_{branch_name}.png")
            return False
        finally:
            await browser.close()

async def main():
    await download_lioren_report("Campanario", "jan_campanario.xlsx")
    await download_lioren_report("Marina", "jan_marina.xlsx")

if __name__ == "__main__":
    asyncio.run(main())
