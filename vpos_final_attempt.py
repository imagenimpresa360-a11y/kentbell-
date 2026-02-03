
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

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
            print("1. Login...")
            await page.goto("https://comercios.virtualpos.cl/login", wait_until='networkidle')
            await page.fill('input[type="email"]', USER)
            await page.fill('input[type="password"]', PASS)
            await page.click('button:has-text("Entrar")')
            
            print("2. Esperando dashboard...")
            await asyncio.sleep(15)
            
            print("3. Navegando a transacciones...")
            await page.goto("https://comercios.virtualpos.cl/finanzas/transacciones", wait_until='networkidle')
            await asyncio.sleep(10)
            
            # Screenshot de la página de transacciones
            await page.screenshot(path=os.path.join(DOWNLOAD_DIR, 'vpos_step3_page.png'))
            
            print("4. Intentando exportar...")
            export_btn = page.locator('button:has-text("Exportar")').first
            
            if await export_btn.count() > 0:
                print("   ✓ Botón Exportar encontrado. Haciendo clic...")
                await export_btn.click()
                await asyncio.sleep(5)
                
                # Capturar para ver si salió un modal o menú
                await page.screenshot(path=os.path.join(DOWNLOAD_DIR, 'vpos_after_export_click.png'))
                
                # Intentar descargar (podría ser Excel o CSV)
                # Buscamos botones de formato comunes
                formats = ["Excel", "CSV", "Confirmar", "Descargar"]
                target_btn = None
                for fmt in formats:
                    btn = page.locator(f'button:has-text("{fmt}"), a:has-text("{fmt}")').first
                    if await btn.count() > 0 and await btn.is_visible():
                        target_btn = btn
                        print(f"   ✓ Botón de formato/confirmación encontrado: {fmt}")
                        break
                
                if target_btn:
                    print("   ✓ Iniciando descarga final...")
                    async with page.expect_download(timeout=120000) as download_info:
                        await target_btn.click()
                    
                    download = await download_info.value
                    path = os.path.join(DOWNLOAD_DIR, download.suggested_filename)
                    await download.save_as(path)
                    print(f"   ✅ ÉXITO: {path}")
                else:
                    print("   ⚠ No se encontró botón secundario, asumiendo que cliquear 'Exportar' debió iniciar descarga...")
                    # Si no hay botón secundario, quizás la descarga ya debió empezar
                    # pero como usamos expect_download antes de clicar, necesitamos replantear
                    print("   Refactorizando para re-intentar clic con expect_download...")
                    try:
                        async with page.expect_download(timeout=10000) as download_info:
                            await export_btn.click()
                        download = await download_info.value
                        path = os.path.join(DOWNLOAD_DIR, download.suggested_filename)
                        await download.save_as(path)
                        print(f"   ✅ ÉXITO (Directo): {path}")
                    except:
                        print("   ❌ Falló descarga directa también.")
            else:
                print("   ❌ No se encontró el botón Exportar")

                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            await page.screenshot(path=os.path.join(DOWNLOAD_DIR, 'vpos_step4_error.png'))
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
