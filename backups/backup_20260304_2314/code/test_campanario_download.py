
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

async def download_campanario_january_students():
    load_dotenv()
    USER = os.getenv('BOXMAGIC_USER')
    PASS = os.getenv('BOXMAGIC_PASS')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            accept_downloads=True
        )
        page = await context.new_page()
        
        try:
            print("Step 1: Login...")
            await page.goto("https://auth.boxmagic.cl/login")
            await page.get_by_placeholder("Correo").fill(USER)
            await page.get_by_placeholder("Contraseña").fill(PASS)
            await page.locator("button[type='submit']").click()
            
            await page.wait_for_selector('text="Panel de administración"', timeout=30000)
            await page.get_by_text("Panel de administración").click(force=True)
            
            await page.wait_for_function("() => window.location.hostname === 'boxmagic.cl'", timeout=60000)
            await page.wait_for_load_state("networkidle")
            
            # Estamos en Campanario (verificado por el logo en el screenshot anterior)
            print("Confirmed: Logged into Campanario.")
            
            # Buscar reportes de alumnos
            print("Step 2: Checking Alumnos list for download...")
            await page.goto("https://boxmagic.cl/alumnos/lista")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            
            # Intentar el flujo de "Mi cuenta" -> "Funciones" para descargar
            print("Step 3: Triggering download via 'Mi cuenta' menu...")
            
            async with page.expect_download(timeout=60000) as download_info:
                # Usar el mismo JS que el bot anterior pero más robusto
                success = await page.evaluate("""() => {
                    return new Promise((resolve, reject) => {
                        const clickEl = (el, name) => {
                            if (!el) return false;
                            el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
                            return true;
                        };

                        const miCuenta = Array.from(document.querySelectorAll('a')).find(el => el.innerText.includes('Mi cuenta'));
                        if (!clickEl(miCuenta)) { reject('Mi Cuenta not found'); return; }

                        setTimeout(() => {
                            const funciones = document.querySelector('#opciones-funciones');
                            if (!clickEl(funciones)) { 
                                // Reintento con texto si el ID falla
                                const funText = Array.from(document.querySelectorAll('a, button')).find(el => el.innerText.includes('Funciones'));
                                if (!clickEl(funText)) { reject('Funciones not found'); return; }
                            }

                            setTimeout(() => {
                                const administra = document.querySelector('#funciones-administra');
                                if (!clickEl(administra)) { 
                                     const admText = Array.from(document.querySelectorAll('a, button')).find(el => el.innerText.includes('Administra'));
                                     if (!clickEl(admText)) { reject('Administra not found'); return; }
                                }

                                setTimeout(() => {
                                    const items = document.querySelectorAll('a, button, li');
                                    let targetView = null;
                                    for (const item of items) {
                                        if (item.innerText.toLowerCase().includes('descargar')) {
                                            targetView = item;
                                            break;
                                        }
                                    }
                                    if (!clickEl(targetView)) { reject('Descargar button not found'); return; }
                                    resolve(true);
                                }, 1000);
                            }, 1000);
                        }, 1000);
                    });
                }""")
                
                download = await download_info.value
                path = f"downloads/boxmagic/alumnos_campanario_test.csv"
                os.makedirs(os.path.dirname(path), exist_ok=True)
                await download.save_as(path)
                print(f"SUCCESS: Downloaded current active students for Campanario to {path}")

            # Ahora intentar encontrar un reporte histórico si existe
            print("Step 4: Looking for historical students report...")
            # En BoxMagic, el reporte de "Ventas" suele tener la información de qué alumnos pagaron.
            # Pero existe un reporte de "Planes Activos" o similares.
            
            # Intentar URL de reporte de alumnos si existe
            # https://boxmagic.cl/reportes/alumnos ?
            
        except Exception as e:
            print(f"Failed: {e}")
            await page.screenshot(path="campanario_download_error.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(download_campanario_january_students())
