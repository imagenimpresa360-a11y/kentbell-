
import asyncio
import os
import csv
from datetime import datetime
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

# Configuración
URL = os.getenv('VIRTUALPOS_URL')
USER = os.getenv('VIRTUALPOS_USER')
PASS = os.getenv('VIRTUALPOS_PASS')
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads", "virtualpos")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

async def run_downloader():
    print("=" * 70)
    print("VIRTUALPOS - DESCARGADOR AUTOMÁTICO")
    print("=" * 70)
    
    async with async_playwright() as p:
        # Usar mismos parámetros que test_vpos_login.py
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768}
        )
        page = await context.new_page()
        
        try:
            # 1. Login
            print("\n[1/4] Realizando login...")
            await page.goto(URL, timeout=90000, wait_until='domcontentloaded')
            print("      ✓ Página inicial cargada")
            
            # Clicar en Acceso Clientes
            await asyncio.sleep(3)
            link = page.get_by_role("link", name="Acceso clientes")
            if await link.count() > 0:
                print("      ✓ Clic en 'Acceso clientes'")
                await link.first.click()
                await asyncio.sleep(5)
            
            # Capturar para ver si estamos en la página de login
            await page.screenshot(path=os.path.join(DOWNLOAD_DIR, 'debug_at_login_page.png'))
            
            # Llenar credenciales (usando selectores probados)
            print("      Intentando llenar credenciales...")
            try:
                # Intentamos por placeholder exacto según la imagen
                await page.fill('input[type="email"]', USER)
                await page.fill('input[type="password"]', PASS)
                print("      ✓ Inputs llenados por tipo")
            except Exception as e:
                print(f"      ⚠ Falló llenado por tipo, intentando por label: {e}")
                await page.get_by_label("Tu Email").fill(USER)
                await page.get_by_label("Tu Contraseña").fill(PASS)
            
            # Clicar en Entrar
            await page.get_by_role("button", name="Entrar").click()
            print("      ✓ Botón Entrar clicaodo")


            
            # Esperar dashboard (paciencia extra)
            print("      ✓ Login enviado, esperando carga de dashboard...")
            await asyncio.sleep(15)
            
            # 2. Navegación a Transacciones
            print("\n[2/4] Navegando a Transacciones...")
            # Ruta directa para mayor fiabilidad una vez logueado
            await page.goto("https://comercios.virtualpos.cl/finanzas/transacciones", wait_until='domcontentloaded')
            await asyncio.sleep(10)
            
            # 3. Descarga de Reporte
            print("\n[3/4] Buscando botón de descarga...")
            # Probamos con "Exportar" que es el que aparece en la UI nueva
            download_button = page.get_by_role("button", name="Exportar").first
            if await download_button.count() == 0:
                download_button = page.get_by_role("button", name="Descargar").first
            
            if await download_button.count() > 0 and await download_button.is_visible():

                print("      ✓ Botón 'Descargar' detectado")
                
                try:
                    async with page.expect_download(timeout=120000) as download_info:
                        await download_button.click()
                        
                        # Manejar posible modal de confirmación
                        await asyncio.sleep(3)
                        confirm_btn = page.get_by_role("button", name="Confirmar")
                        if await confirm_btn.count() > 0:
                            print("      ✓ Confirmando descarga en modal...")
                            await confirm_btn.click()
                            
                    download = await download_info.value
                    filename = download.suggested_filename
                    save_path = os.path.join(DOWNLOAD_DIR, filename)
                    await download.save_as(save_path)
                    print(f"\n[4/4] ✅ ÉXITO: {filename} descargado.")
                    return save_path
                except Exception as down_err:
                    print(f"      ❌ Error durante la descarga: {down_err}")
            else:
                print("      ❌ No se encontró el botón de descarga visible.")
                await page.screenshot(path=os.path.join(DOWNLOAD_DIR, 'debug_no_download_btn.png'))
                
        except Exception as e:
            print(f"\n      ❌ ERROR GLOBAL: {e}")
            await page.screenshot(path=os.path.join(DOWNLOAD_DIR, 'critical_error.png'))
        finally:
            await browser.close()
            print("\n" + "=" * 70)

if __name__ == "__main__":
    asyncio.run(run_downloader())
