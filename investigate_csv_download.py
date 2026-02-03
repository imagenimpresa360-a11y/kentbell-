import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

LARAVEL_SESSION = "eyJpdiI6InFzbWhtMHA3WHJvNmFJUmlLY3NpQ0E9PSIsInZhbHVlIjoiZW5ucCtXVUhXWGtyMDE3N2lzUmpoVTZcL3Q0RFpCQ2pDdzgwMjlzbjBUYWFLeE4zXC9oNUc0cUEyeWxYM2pnSGpNK2NHZkkxbmFudUVYWUZMNm5HcTdpUT09IiwibWFjIjoiOTY3OGZiMDQzNzE1YmY0MGZkNTg3NTdjOTM3N2MzZmE0YWJmYzcxZmI0MTY1NTBiOGNlZmNmOWVmOWFhZTcwMiJ9"
DOMAIN = "boxmagic.cl"
URL_REPORTS = "https://boxmagic.cl/reportes/v2/reportes_pagos"

async def main():
    print("--- INVESTIGANDO DESCARGA CSV DE BOXMAGIC ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visible para debugging
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768},
            accept_downloads=True
        )
        
        await context.add_cookies([{'name': 'laravel_session', 'value': LARAVEL_SESSION, 'domain': DOMAIN, 'path': '/'}])
        page = await context.new_page()
        
        try:
            print(f"1. Navegando a {URL_REPORTS}...")
            await page.goto(URL_REPORTS, timeout=60000, wait_until='domcontentloaded')
            print("   ✓ DOM cargado")
            
            # Esperar que aparezca la tabla (indicador de que la página está lista)
            await page.wait_for_selector('table', timeout=30000)
            print("   ✓ Tabla de datos cargada")
            
            # Pequeña espera adicional para que se inicialicen los botones
            await asyncio.sleep(2)
            
            if "login" in page.url:
                raise Exception("Sesión expirada")

            print("2. Página de reportes cargada")
            
            # Buscar todos los botones CSV
            csv_buttons = page.locator("button:has-text('CSV')")
            count = await csv_buttons.count()
            print(f"3. Encontrados {count} botones con texto 'CSV'")
            
            for i in range(count):
                btn = csv_buttons.nth(i)
                is_visible = await btn.is_visible()
                classes = await btn.get_attribute('class')
                print(f"   Botón {i}: Visible={is_visible}, Classes={classes}")
            
            # Intentar con el botón visible
            visible_csv = page.locator(".buttons-csv:visible").first
            if await visible_csv.count() > 0:
                print("\n4. Intentando clic en botón .buttons-csv:visible")
                
                # Configurar listener de descarga ANTES del clic
                async with page.expect_download(timeout=90000) as download_info:
                    await visible_csv.click()
                    print("   ✓ Clic ejecutado, esperando descarga...")
                
                download = await download_info.value
                print(f"   ✓ Descarga iniciada: {download.suggested_filename}")
                
                # Guardar archivo
                save_path = os.path.join(os.getcwd(), "downloads", download.suggested_filename)
                await download.save_as(save_path)
                print(f"   ✓ Archivo guardado: {save_path}")
                print(f"   ✓ Tamaño: {os.path.getsize(save_path)} bytes")
            else:
                print("\n⚠ No se encontró botón CSV visible")
            
            # Mantener abierto para inspección
            print("\n5. Manteniendo navegador abierto 15 segundos...")
            await asyncio.sleep(15)
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path='debug_csv_investigation.png')
            
        finally:
            await browser.close()
            print("\n--- INVESTIGACIÓN FINALIZADA ---")

if __name__ == "__main__":
    asyncio.run(main())
