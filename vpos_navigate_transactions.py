
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv('VIRTUALPOS_URL')
USER = os.getenv('VIRTUALPOS_USER')
PASS = os.getenv('VIRTUALPOS_PASS')
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads", "virtualpos")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768}
        )
        page = await context.new_page()
        
        try:
            print("[1/4] Iniciando sesión...")
            await page.goto(URL, timeout=90000)
            
            # Clic en Acceso clientes
            await page.get_by_role("link", name="Acceso clientes").first.click()
            await page.wait_for_load_state('networkidle')
            
            # Llenar login
            await page.locator('input[type="email"]').fill(USER)
            await page.locator('input[type="password"]').fill(PASS)
            await page.get_by_role("button", name="Entrar").click()
            
            # Esperar dashboard
            await asyncio.sleep(10)
            print(f"      Dashboard cargado: {page.url}")
            
            # 2. Navegar a Transacciones
            print("[2/4] Buscando sección de Transacciones...")
            # Opción 1: Clic en el menú (más seguro si hay redirecciones JS)
            # Primero clicamos el item de "Transacciones" que abre el submenú
            await page.locator('a[title="Transacciones"]').click()
            await asyncio.sleep(2)
            
            # Ahora clicamos el link real dentro del submenú
            # Según el HTML es: <a href="/finanzas/transacciones">Transacciones</a>
            await page.locator('div.subMenu a[href="/finanzas/transacciones"]').click()
            
            # Esperar carga de la página de transacciones
            await asyncio.sleep(10)
            print(f"      Sección de transacciones cargada: {page.url}")
            await page.screenshot(path=os.path.join(DOWNLOAD_DIR, 'page_transacciones.png'))
            
            # 3. Buscar botón de descarga
            print("[3/4] Buscando botón de exportación...")
            # El botón "Descargar" en esta página suele abrir un modal o descargar directo
            download_btn = page.get_by_role("button", name="Descargar").first
            
            if await download_btn.count() > 0:
                print("      ✓ Botón 'Descargar' encontrado")
                
                # 4. Descargar
                print("[4/4] Ejecutando descarga...")
                async with page.expect_download(timeout=60000) as download_info:
                    await download_btn.click()
                    
                    # Si al clicar aparece un modal avisando que se está preparando el archivo 
                    # o pidiendo confirmar formato, Playwright esperará al evento de descarga.
                    # Si es un modal, puede que necesitemos clicar OTRA VEZ en "Confirmar" o similar.
                    # Vamos a ver si aparece algo extra.
                    await asyncio.sleep(2)
                    confirm_btn = page.get_by_role("button", name="Confirmar")
                    if await confirm_btn.count() > 0:
                        print("      ✓ Confirmando en el modal...")
                        await confirm_btn.click()
                
                download = await download_info.value
                path = os.path.join(DOWNLOAD_DIR, download.suggested_filename)
                await download.save_as(path)
                print(f"      ✅ ÉXITO: Archivo guardado en {path}")
            else:
                print("      ❌ No se encontró el botón 'Descargar'")
                # Captura para ver qué hay
                await page.screenshot(path=os.path.join(DOWNLOAD_DIR, 'error_no_button.png'))
                # Guardar HTML para debug
                content = await page.content()
                with open(os.path.join(DOWNLOAD_DIR, 'page_transacciones.html'), 'w', encoding='utf-8') as f:
                    f.write(content)
                    
        except Exception as e:
            print(f"      ❌ ERROR: {e}")
            await page.screenshot(path=os.path.join(DOWNLOAD_DIR, 'error_vpos_nav.png'))
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
