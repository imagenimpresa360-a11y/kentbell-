
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

async def download_vpos_transactions():
    print("=" * 70)
    print("VIRTUALPOS - DESCARGA DE TRANSACCIONES")
    print("=" * 70)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768}
        )
        
        page = await context.new_page()
        
        try:
            # 1. Login
            print("\n[1/4] Realizando login...")
            # Navegar directamente al subdominio de comercios/login
            LOGIN_URL = "https://comercios.virtualpos.cl/login"
            await page.goto(LOGIN_URL, timeout=90000, wait_until='networkidle')
            
            # Buscar campos de login
            print("      Buscando campos de entrada...")
            
            # Los campos tienen placeholders específicos: "Tu Email" y "Tu Contraseña"
            await page.wait_for_selector('input[placeholder*="Email"]', timeout=30000)
            
            email_field = page.locator('input[placeholder*="Email"]').first
            password_field = page.locator('input[placeholder*="Contraseña"]').first
            
            await email_field.fill(USER)
            await password_field.fill(PASS)
            
            # Clic en "Entrar"
            await page.get_by_role("button", name="Entrar").click()
            
            # Esperar dashboard
            print("      ✓ Credenciales enviadas, esperando dashboard...")
            await asyncio.sleep(10)

            
            if "login" in page.url.lower():
                print("      ❌ Error: Sigue en página de login. ¿Captcha?")
                await page.screenshot(path=os.path.join(DOWNLOAD_DIR, 'vpos_login_failed.png'))
                return

            print(f"      ✓ Dashboard cargado: {page.url}")
            
            # 2. Navegar a Transacciones
            print("\n[2/4] Navegando a la sección de Transacciones...")
            # Navegación directa a la página de finanzas
            await page.goto("https://comercios.virtualpos.cl/finanzas/transacciones", wait_until='domcontentloaded')
            await asyncio.sleep(8) # Dar tiempo a que cargue la SPA
            
            print(f"      Página actual: {await page.title()}")
            await page.screenshot(path=os.path.join(DOWNLOAD_DIR, 'vpos_transacciones_page.png'))
            
            # 3. Buscar botón de descarga/exportación
            print("\n[3/4] Buscando botón de exportación...")
            
            # En VirtualPOS 2.0 el botón de exportar suele estar arriba a la derecha
            # Buscamos por texto o por ícono de descarga
            export_keywords = ["Descargar", "Exportar", "Excel", "CSV"]
            export_button = None
            
            for keyword in export_keywords:
                # Buscar botones que CONTENGAN el texto
                btn = page.locator(f'button:has-text("{keyword}")').first
                if await btn.count() > 0 and await btn.is_visible():
                    export_button = btn
                    print(f"      ✓ Encontrado botón por texto: {keyword}")
                    break
            
            if not export_button:
                # Buscar por ícono (algunos usan íconos de FontAwesome o SVG)
                # Intentar clics en elementos que parecen de descarga
                selectors = ['.btn-outline-secondary', '.btn-primary', 'a[href*="export"]', 'button[title*="Descargar"]']
                for selector in selectors:
                    try:
                        loc = page.locator(selector).first
                        if await loc.count() > 0:
                            text = await loc.inner_text()
                            if any(k.lower() in text.lower() for k in export_keywords):
                                export_button = loc
                                print(f"      ✓ Encontrado botón por selector: {selector} ({text.strip()})")
                                break
                    except:
                        continue

            if export_button:
                # 4. Iniciar descarga
                print("\n[4/4] Iniciando descarga...")
                try:
                    async with page.expect_download(timeout=60000) as download_info:
                        await export_button.click()
                    
                    download = await download_info.value
                    filename = download.suggested_filename
                    download_path = os.path.join(DOWNLOAD_DIR, filename)
                    await download.save_as(download_path)
                    
                    print(f"      ✓ Descarga completada: {filename}")
                    print(f"      ✓ Ubicación: {download_path}")
                except Exception as down_error:
                    print(f"      ❌ Fallo en la descarga: {down_error}")
            else:
                print("      ❌ No se encontró el botón de exportación visualmente.")
                # Intentar buscar en el HTML si hay algún link oculto
                links = await page.locator('a').all()
                for link in links:
                    href = await link.get_attribute('href') or ""
                    if "export" in href.lower() or "download" in href.lower():
                        print(f"      🎯 Link potencial encontrado: {href}")
                
                await page.screenshot(path=os.path.join(DOWNLOAD_DIR, 'vpos_no_export_button.png'))


        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            await page.screenshot(path=os.path.join(DOWNLOAD_DIR, 'vpos_error_final.png'))
            
        finally:
            await browser.close()
            print("\nProceso finalizado.")

if __name__ == "__main__":
    asyncio.run(download_vpos_transactions())
