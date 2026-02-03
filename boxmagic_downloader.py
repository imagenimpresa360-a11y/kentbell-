"""
BoxMagic Report Downloader - Versión de Producción
Descarga automáticamente el reporte de ventas de BoxMagic usando inyección de sesión
"""
import asyncio
import os
from datetime import datetime
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

# Configuración
LARAVEL_SESSION = "eyJpdiI6InFzbWhtMHA3WHJvNmFJUmlLY3NpQ0E9PSIsInZhbHVlIjoiZW5ucCtXVUhXWGtyMDE3N2lzUmpoVTZcL3Q0RFpCQ2pDdzgwMjlzbjBUYWFLeE4zXC9oNUc0cUEyeWxYM2pnSGpNK2NHZkkxbmFudUVYWUZMNm5HcTdpUT09IiwibWFjIjoiOTY3OGZiMDQzNzE1YmY0MGZkNTg3NTdjOTM3N2MzZmE0YWJmYzcxZmI0MTY1NTBiOGNlZmNmOWVmOWFhZTcwMiJ9"
DOMAIN = "boxmagic.cl"
URL_REPORTS = "https://boxmagic.cl/reportes/v2/reportes_pagos"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads", "boxmagic")

# Crear directorio de descargas
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

async def download_boxmagic_report(headless=True):
    """
    Descarga el reporte de ventas de BoxMagic
    
    Args:
        headless (bool): Si True, ejecuta el navegador en modo headless
        
    Returns:
        str: Ruta del archivo descargado o None si falla
    """
    print("=" * 70)
    print("BOXMAGIC - DESCARGADOR AUTOMÁTICO DE REPORTES")
    print("=" * 70)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768},
            accept_downloads=True
        )
        
        # Inyectar sesión
        print(f"\n[1/5] Inyectando cookie de sesión...")
        await context.add_cookies([{
            'name': 'laravel_session', 
            'value': LARAVEL_SESSION, 
            'domain': DOMAIN, 
            'path': '/'
        }])
        print("      ✓ Cookie inyectada")
        
        page = await context.new_page()
        downloaded_file = None
        
        try:
            # Navegar a reportes
            print(f"\n[2/5] Navegando a página de reportes...")
            await page.goto(URL_REPORTS, timeout=60000, wait_until='domcontentloaded')
            print("      ✓ DOM cargado")
            
            # Esperar tabla de datos
            await page.wait_for_selector('table', timeout=30000)
            print("      ✓ Tabla de datos cargada")
            
            # Espera adicional para inicialización de botones
            await asyncio.sleep(2)
            
            # Verificar que no estamos en login
            if "login" in page.url:
                raise Exception("Cookie de sesión expirada. Necesita renovación.")
            
            print("      ✓ Acceso confirmado")
            
            # Buscar botón CSV
            print(f"\n[3/5] Localizando botón de exportación CSV...")
            csv_button = page.locator(".buttons-csv:visible").first
            
            if await csv_button.count() == 0:
                raise Exception("No se encontró el botón de exportación CSV")
            
            print("      ✓ Botón CSV encontrado")
            
            # Descargar archivo
            print(f"\n[4/5] Iniciando descarga...")
            async with page.expect_download(timeout=90000) as download_info:
                await csv_button.click()
                print("      ✓ Clic en botón CSV ejecutado")
            
            download = await download_info.value
            filename = download.suggested_filename
            print(f"      ✓ Descarga iniciada: {filename}")
            
            # Guardar con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_filename = f"boxmagic_ventas_{timestamp}.csv"
            save_path = os.path.join(DOWNLOAD_DIR, final_filename)
            
            await download.save_as(save_path)
            file_size = os.path.getsize(save_path)
            
            print(f"\n[5/5] Descarga completada")
            print(f"      ✓ Archivo: {final_filename}")
            print(f"      ✓ Ubicación: {save_path}")
            print(f"      ✓ Tamaño: {file_size} bytes")
            
            downloaded_file = save_path
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            await page.screenshot(path='error_boxmagic_download.png')
            print(f"   Screenshot guardado: error_boxmagic_download.png")
            
        finally:
            await browser.close()
            print("\n" + "=" * 70)
            
        return downloaded_file

async def main():
    """Función principal"""
    result = await download_boxmagic_report(headless=True)
    
    if result:
        print(f"\n✅ ÉXITO: Reporte descargado en {result}")
        return 0
    else:
        print(f"\n❌ FALLO: No se pudo descargar el reporte")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
